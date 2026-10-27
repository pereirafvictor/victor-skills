"""
subir-campanha — modelo CHATBOT (anúncio abre o Messenger da página, conversão no pixel).

Sobe N campanhas a partir de um plano JSON: **1 campanha por página**, 1 conjunto, 2-5 anúncios.
Tudo que é da conta (conta, pixel, evento, países, páginas, padrão de nome/UTM) vem do
config.chatbot.json da skill — copie config.chatbot.example.json e preencha. O token vem do .env.

Todo conjunto sai com:
  - destino MESSENGER, posicionamentos SÓ Facebook + Messenger (sem Instagram/Threads)
  - ad_set_goal = {"type": 0}  → "Estratégia de ciclo de vida do cliente" = Obter conversões de todos os públicos
  - targeting_automation = {"advantage_audience": 1}  → Advantage+ Audience
Todo anúncio sai com CTA MESSAGE_PAGE, mensagem de boas-vindas (ice breakers) e a UTM da PÁGINA em url_tags
(o GAM soma por página — a UTM não leva número de campanha).

Uso:
  python scripts/subir_chatbot.py plano.json --dry-run
  python scripts/subir_chatbot.py plano.json            # cria (retoma de onde parou se cair)
  python scripts/subir_chatbot.py plano.json --conferir # só confere as já criadas pelo log
  --config outro.json                                   # usa outro arquivo de configuração

Formato do plano e do config: ver SKILL.md.
"""
import argparse
import collections
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import subir_direto as sd  # noqa: E402  (reaproveita cliente da API, subida de vídeo e OPT_OUT do criativo)
from subir_direto import AD_SET_GOAL, Meta  # noqa: E402

SKILL_DIR = sd.SKILL_DIR
NOME_PADRAO = "[{data}][{site}][{oferta}][{bloco_pais}][{pagina_slug}][chatbot] - {nn}"
UTM_PADRAO = "{utm_prefixo}-{idioma}-{pais_min}-{pagina_slug}-chatbot"
CTA = {"type": "MESSAGE_PAGE", "value": {"app_destination": "MESSENGER"}}

CFG = {}
CONTA = PIXEL = None
PAISES = {}   # ISO: {"idioma", "bloco", "ue"}
PAGINAS = {}  # slug: {"id", "nome", "pais"}


def carregar_config(caminho):
    global CFG, CONTA, PIXEL, PAISES, PAGINAS
    if not Path(caminho).exists():
        sys.exit(f"✗ Config não encontrado: {caminho}\n"
                 "  Copie config.chatbot.example.json pra config.chatbot.json e preencha com a sua conta.")
    CFG = json.load(open(caminho, encoding="utf-8"))
    faltando = [k for k in ("conta", "pixel", "site", "oferta", "utm_prefixo", "paises", "paginas") if not CFG.get(k)]
    if faltando:
        sys.exit(f"✗ Faltam no config: {', '.join(faltando)}")
    CONTA = CFG["conta"] if str(CFG["conta"]).startswith("act_") else f"act_{CFG['conta']}"
    PIXEL = str(CFG["pixel"])
    PAISES, PAGINAS = CFG["paises"], CFG["paginas"]
    for slug, p in PAGINAS.items():
        if p.get("pais") not in PAISES:
            sys.exit(f"✗ Página {slug}: país '{p.get('pais')}' não cadastrado em \"paises\" no config.")
    sd.CONTA = CONTA  # subir_video / dof_opt_out do modelo direto usam a conta do módulo


def boas_vindas(texto, botoes):
    """page_welcome_message no formato que o Ads Manager grava: texto + ice breakers sem resposta."""
    return json.dumps({
        "type": "VISUAL_EDITOR", "version": 2, "landing_screen_type": "welcome_message", "media_type": "text",
        "text_format": {"customer_action_type": "ice_breakers",
                        "message": {"text": texto, "ice_breakers": [{"title": b} for b in botoes], "quick_replies": []}},
        "user_edit": False, "surface": "visual_editor_new"}, ensure_ascii=False)


def numero_max(meta):
    """Maior número já usado por (data, página) — 2ª campanha da mesma página no mesmo dia vira '- 2'."""
    mx = collections.defaultdict(int)
    for c in meta.get(f"{CONTA}/campaigns", fields="name", limit=500):
        m = re.match(r"\[([\d/]+)\].*\[(\w+)\]\[chatbot\].*- (\d+)\s*$", c["name"])
        if m:
            mx[(m.group(1), m.group(2))] = max(mx[(m.group(1), m.group(2))], int(m.group(3)))
    return mx


def publicos_modelo(meta, paises):
    """Público de cada país = o do conjunto de chatbot mais recente do país. País sem histórico usa o padrão.
    Posicionamentos são forçados pra Facebook + Messenger em qualquer caso."""
    tpl = {}
    rows = meta.get(f"{CONTA}/adsets", fields="campaign{name},targeting,attribution_spec,created_time", limit=200)
    for a in sorted(rows, key=lambda a: a["created_time"]):
        if "[chatbot]" in a["campaign"]["name"]:
            for p in a["targeting"].get("geo_locations", {}).get("countries", []):
                tpl[p] = {"targeting": a["targeting"], "attribution_spec": a["attribution_spec"]}
    for p in paises:
        if p not in tpl:
            tpl[p] = {"targeting": {"geo_locations": {"countries": [p], "location_types": ["frequently_in", "home", "recent"]},
                                    "age_min": 18, "age_max": 65, "device_platforms": ["mobile", "desktop"]},
                      "attribution_spec": [{"event_type": "CLICK_THROUGH", "window_days": 7},
                                           {"event_type": "VIEW_THROUGH", "window_days": 1},
                                           {"event_type": "ENGAGED_VIDEO_VIEW", "window_days": 1}]}
            print(f"  ⚠ {p}: sem conjunto de chatbot anterior na conta — usando público padrão (18-65, celular+desktop)")
    for p, t in tpl.items():
        tg = {k: v for k, v in t["targeting"].items() if not k.startswith(("instagram", "threads"))}
        tg.update({"publisher_platforms": ["facebook", "messenger"],
                   "facebook_positions": ["feed", "story", "facebook_reels"],
                   "messenger_positions": ["messenger_home"],
                   "targeting_automation": {"advantage_audience": 1}})
        t["targeting"] = tg
    return tpl


def criativos_existentes(meta):
    """criativo → {idioma: video_data} do anúncio de chatbot mais recente chamado '{criativo} - {Página}'."""
    idx = collections.defaultdict(dict)
    por_id = {p["id"]: p for p in PAGINAS.values()}
    ads = meta.get(f"{CONTA}/ads", fields="name,created_time,campaign{name},creative{object_story_spec}", limit=50)
    for a in sorted(ads, key=lambda a: a["created_time"]):
        oss = a["creative"].get("object_story_spec", {})
        pag = por_id.get(oss.get("page_id"))
        if "[chatbot]" not in a["campaign"]["name"] or "video_data" not in oss or not pag:
            continue
        vd = oss["video_data"]
        idx[a["name"].rsplit(" - ", 1)[0]][PAISES[pag["pais"]]["idioma"]] = {
            "video_id": vd["video_id"], "image_hash": vd.get("image_hash"),
            "image_url": None if vd.get("image_hash") else vd.get("image_url"),
            "message": vd.get("message", ""), "title": vd.get("title"), "desc": vd.get("link_description"),
            "boas_vindas": vd.get("page_welcome_message")}
    return idx


def resolver_criativo(cr, idioma, idx):
    """String = criativo que já roda em chatbot do mesmo idioma; objeto = vídeo novo com boas-vindas."""
    if isinstance(cr, str):
        if cr not in idx or idioma not in idx[cr]:
            sys.exit(f"✗ Criativo '{cr}' não encontrado em anúncio de chatbot [{idioma}] na conta.")
        return cr, dict(idx[cr][idioma])
    bv = cr.get("boas_vindas") or {}
    if not bv.get("texto") or not bv.get("botoes"):
        sys.exit(f"✗ Criativo novo '{cr.get('video')}': falta \"boas_vindas\" com \"texto\" e \"botoes\".")
    if not Path(cr["video"]).exists():
        sys.exit(f"✗ Vídeo não existe: {cr['video']}")
    nome = cr.get("nome") or Path(cr["video"]).stem[:60]
    return nome, {"novo": cr["video"], "message": cr["texto"], "title": cr.get("titulo"),
                  "desc": cr.get("descricao", CFG.get("descricao_padrao")),
                  "boas_vindas": boas_vindas(bv["texto"], bv["botoes"])}


def conferir(meta, log):
    st, ruins = collections.Counter(), []
    for c in log:
        d = meta.get(c["campaign_id"], fields="name,effective_status,adsets{ad_set_goal,destination_type,"
                                               "targeting{targeting_automation,publisher_platforms}},"
                                               "ads{effective_status,creative{url_tags,call_to_action_type}}")
        a = d["adsets"]["data"][0]
        st["campanha " + d["effective_status"]] += 1
        problemas = []
        for ad in d["ads"]["data"]:
            st["anúncio " + ad["effective_status"]] += 1
            if ad["creative"].get("url_tags") != c["utm"]:
                problemas.append("anúncio sem UTM da página")
            if ad["creative"].get("call_to_action_type") != "MESSAGE_PAGE":
                problemas.append("CTA não é MESSAGE_PAGE")
        if (a.get("ad_set_goal") or {}).get("type") != 0:
            problemas.append("ciclo de vida vazio")
        if a["targeting"].get("targeting_automation", {}).get("advantage_audience") != 1:
            problemas.append("advantage_audience off")
        if a.get("destination_type") != "MESSENGER":
            problemas.append("destino não é Messenger")
        if set(a["targeting"].get("publisher_platforms", [])) - {"facebook", "messenger"}:
            problemas.append("posicionamento fora de FB+Messenger")
        if problemas:
            ruins.append((d["name"], sorted(set(problemas))))
            if "ciclo de vida vazio" in problemas:  # corrige na hora
                meta.post(a["id"], {"ad_set_goal": AD_SET_GOAL})
                print(f"  ✔ ciclo de vida corrigido: {d['name']}")
    print(f"\nConferência: {len(log)} campanhas — {dict(st)}")
    for n, p in ruins:
        print(f"  ⚠ {n}: {', '.join(p)}")
    if log:
        print(f"\nPra conferir no Ads Manager (recarregue a página): {log[0]['name']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plano")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--conferir", action="store_true")
    ap.add_argument("--config", default=str(SKILL_DIR / "config.chatbot.json"))
    args = ap.parse_args()
    carregar_config(args.config)
    plano = json.load(open(args.plano, encoding="utf-8"))
    token = os.getenv("META_ACCESS_TOKEN") or sys.exit("✗ META_ACCESS_TOKEN ausente no .env")
    meta = Meta(token)

    log_path = Path(args.plano).with_suffix(".log.json")
    log = json.load(open(log_path, encoding="utf-8")) if log_path.exists() else []
    if args.conferir:
        return conferir(meta, log)

    evento = plano.get("evento", CFG.get("evento_padrao", "SEARCH"))
    orcamento_plano = plano.get("orcamento", CFG.get("orcamento_padrao", 5))
    inicio = plano.get("inicio", "amanha")  # "amanha" = ACTIVE agendado 00:01 · "agora" = ACTIVE · "pausada" = PAUSED
    data = plano.get("data") or (datetime.now() + timedelta(days=1 if inicio == "amanha" else 0)).strftime("%d/%m")
    campanhas = plano["campanhas"]

    # regra: 1 campanha por página
    paginas = [c["pagina"] for c in campanhas]
    for slug in paginas:
        if slug not in PAGINAS:
            sys.exit(f"✗ Página '{slug}' não cadastrada em \"paginas\" no config.")
        if paginas.count(slug) > 1:
            sys.exit(f"✗ Página '{slug}' aparece {paginas.count(slug)}x no plano — chatbot é 1 campanha por página.")
    for c in campanhas:
        if not c.get("criativos"):
            sys.exit(f"✗ Página '{c['pagina']}' sem criativos no plano.")

    paises = sorted({PAGINAS[s]["pais"] for s in paginas})
    mx = numero_max(meta)
    tpl = publicos_modelo(meta, paises)
    idx = criativos_existentes(meta)
    dof = None if args.dry_run else sd.dof_opt_out(meta)
    feitos = {l["chave"] for l in log}
    novos_videos = {}

    print(f"Plano: {len(campanhas)} campanhas · conta {CONTA} · evento {evento} · início {inicio} · "
          f"Messenger · FB+Messenger · ciclo de vida = todos os públicos · Advantage+ Audience ligado\n")
    criadas = 0
    for i, c in enumerate(campanhas):
        slug = c["pagina"]
        chave = f"{i}:{slug}"
        if chave in feitos:
            continue
        pag = PAGINAS[slug]
        pais = pag["pais"]
        idioma = PAISES[pais]["idioma"]
        mx[(data, slug)] += 1
        nome = CFG.get("nome", NOME_PADRAO).format(
            data=data, site=CFG["site"], oferta=CFG["oferta"], bloco_pais=PAISES[pais]["bloco"],
            pagina_slug=slug, nn=mx[(data, slug)])
        utm = "utm_source=facebook&utm_campaign=" + CFG.get("utm", UTM_PADRAO).format(
            utm_prefixo=CFG["utm_prefixo"], idioma=idioma, pais=pais, pais_min=pais.lower(), pagina_slug=slug)
        orcamento = int(round(float(c.get("orcamento", orcamento_plano)) * 100))
        crs = [resolver_criativo(cr, idioma, idx) for cr in c["criativos"]]
        anuncios = ", ".join(f"{n} - {pag['nome']}" for n, _ in crs)
        print(f"{nome}  ${orcamento / 100:.0f}/dia\n   {anuncios}\n   {utm}")
        if args.dry_run:
            continue

        status = "PAUSED" if inicio == "pausada" else "ACTIVE"
        camp = meta.post(f"{CONTA}/campaigns", {
            "name": nome, "objective": "OUTCOME_SALES", "status": status, "special_ad_categories": [],
            "daily_budget": orcamento, "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "is_adset_budget_sharing_enabled": "false"})["id"]
        conj = {
            "name": nome, "campaign_id": camp, "status": status,
            "optimization_goal": "OFFSITE_CONVERSIONS", "billing_event": "IMPRESSIONS", "destination_type": "MESSENGER",
            "targeting": tpl[pais]["targeting"], "attribution_spec": tpl[pais]["attribution_spec"],
            "ad_set_goal": AD_SET_GOAL,
            "promoted_object": {"pixel_id": PIXEL, "custom_event_type": evento, "page_id": pag["id"]}}
        if PAISES[pais].get("ue") and CFG.get("dsa_beneficiario"):  # obrigatório pra países da UE
            conj["dsa_beneficiary"] = conj["dsa_payor"] = CFG["dsa_beneficiario"]
        if inicio == "amanha":
            amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            conj["start_time"] = f"{amanha}T00:01:00{CFG.get('fuso', '-0700')}"
        conjunto = meta.post(f"{CONTA}/adsets", conj)["id"]

        ids = []
        for nome_cr, s in crs:
            if "novo" in s:
                if s["novo"] not in novos_videos:
                    novos_videos[s["novo"]] = sd.subir_video(meta, s["novo"], nome_cr)
                vid, thumb = novos_videos[s["novo"]]
                s = {**s, "video_id": vid, "image_url": thumb}
            vd = {"video_id": s["video_id"], "message": s["message"], "call_to_action": CTA,
                  "page_welcome_message": s["boas_vindas"]}
            if s.get("title"):
                vd["title"] = s["title"]
            if s.get("desc"):
                vd["link_description"] = s["desc"]
            if s.get("image_hash"):
                vd["image_hash"] = s["image_hash"]
            else:
                vd["image_url"] = s["image_url"]
            nome_ad = f"{nome_cr} - {pag['nome']}"
            corpo = {"name": nome_ad, "object_story_spec": {"page_id": pag["id"], "video_data": vd}, "url_tags": utm}
            if dof:
                corpo["degrees_of_freedom_spec"] = dof
            cr_id = meta.post(f"{CONTA}/adcreatives", corpo)["id"]
            ids.append(meta.post(f"{CONTA}/ads", {"name": nome_ad, "adset_id": conjunto,
                                                  "creative": {"creative_id": cr_id}, "status": status})["id"])

        log.append({"chave": chave, "name": nome, "utm": utm, "campaign_id": camp, "adset_id": conjunto, "ads": ids})
        json.dump(log, open(log_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        criadas += 1
        print(f"   ✔ criada {time.strftime('%H:%M')}", flush=True)
        if criadas % 5 == 0 and i < len(campanhas) - 1:  # lote de 5 + pausa: evita o bloqueio de API da conta
            print("  ⏸ pausa de 5 min entre lotes", flush=True)
            time.sleep(300)

    if args.dry_run:
        print(f"\nDRY-RUN: {len(campanhas)} campanhas. Nada foi criado.")
        return
    conferir(meta, log)
    print(f"\nAds Manager: https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={CONTA.replace('act_', '')}")


if __name__ == "__main__":
    main()
