"""
subir-campanha — modelo DIRETO (tráfego direto pro site, conversão no pixel).

Sobe N campanhas a partir de um plano JSON, cada uma 1 campanha × 1 conjunto × 3-4 anúncios.
Tudo que é da conta de quem usa (conta, página, pixel, site, funis, países, padrão de nome/UTM)
vem do config.json da skill — copie config.example.json e preencha. O token vem do .env.

Todo conjunto sai com:
  - ad_set_goal = {"type": 0}  → "Estratégia de ciclo de vida do cliente" = Obter conversões de todos os públicos
  - targeting_automation = {"advantage_audience": 1}  → Advantage+ Audience
Sem o ad_set_goal o dropdown de ciclo de vida fica VAZIO no Ads Manager.

Uso:
  python scripts/subir_direto.py plano.json --dry-run
  python scripts/subir_direto.py plano.json            # cria (retoma de onde parou se cair)
  python scripts/subir_direto.py plano.json --conferir # só confere as já criadas pelo log
  --config outro.json                                  # usa outro arquivo de configuração

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

import requests
from dotenv import load_dotenv

SKILL_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SKILL_DIR / ".env")
load_dotenv(Path.home() / ".meta-ads" / ".env")  # instalação pelo pacote-gestor guarda o token aqui

G = "https://graph.facebook.com/v21.0/"
GV = "https://graph-video.facebook.com/v21.0/"
AD_SET_GOAL = {"type": 0}           # 0 = Obter conversões de todos os públicos
LIMITE = ("\"code\":17", "\"code\":4,", "\"code\":32", "\"code\":613", "\"code\":80004")
NOME_PADRAO = "[{data}][{modelo}]{blocos}[{continente}][{pais}][{idioma}][{nicho}][{site}][{pagina_slug}] - {nn}"
UTM_PADRAO = "{utm_prefixo}-{idioma}-{pais_min}-{pagina_slug}-{nn}"

CFG = {}      # preenchido por carregar_config()
CONTA = PAGINA = PIXEL = None
PAISES = {}   # ISO: (idioma, continente, nome do conjunto, 1ª linha padrão do texto)


def carregar_config(caminho):
    global CFG, CONTA, PAGINA, PIXEL, PAISES
    if not Path(caminho).exists():
        sys.exit(f"✗ Config não encontrado: {caminho}\n  Copie config.example.json pra config.json e preencha com a sua conta.")
    CFG = json.load(open(caminho, encoding="utf-8"))
    faltando = [k for k in ("conta", "pagina_id", "pagina_slug", "pixel", "site", "utm_prefixo", "funis", "paises")
                if not CFG.get(k)]
    if faltando:
        sys.exit(f"✗ Faltam no config: {', '.join(faltando)}")
    CONTA = CFG["conta"] if str(CFG["conta"]).startswith("act_") else f"act_{CFG['conta']}"
    PAGINA, PIXEL = str(CFG["pagina_id"]), str(CFG["pixel"])
    PAISES = {iso: (p["idioma"], p["continente"], p["conjunto"], p.get("primeira_linha", ""))
              for iso, p in CFG["paises"].items()}


def trocar_primeira_linha(texto, primeira):
    """Se o texto começa com a 1ª linha padrão de algum país do config, troca pela do país da campanha."""
    if not primeira:
        return texto
    linha, sep, resto = texto.partition("\n")
    if linha.strip() in {p[3] for p in PAISES.values() if p[3]}:
        return primeira + sep + resto
    return texto


class Meta:
    def __init__(self, token):
        self.token = token

    def _req(self, metodo, url, **kw):
        for _ in range(40):
            r = requests.request(metodo, url, timeout=120, **kw)
            if r.ok:
                return r.json()
            if any(c in r.text for c in LIMITE):
                print("  ⏳ limite de API da Meta — esperando 5 min", flush=True)
                time.sleep(300)
                continue
            sys.exit(f"✗ ERRO Meta ({url.split('?')[0].replace(G, '')}): {r.text[:600]}")
        sys.exit("✗ Limite de API não liberou depois de várias tentativas.")

    def get(self, path, **p):
        p["access_token"] = self.token
        out, url = [], G + path
        while url:
            d = self._req("GET", url, params=p)
            p = None
            if "data" not in d:
                return d
            out += d["data"]
            url = d.get("paging", {}).get("next")
        return out

    def post(self, path, data, base=G, files=None):
        data = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in data.items()}
        data["access_token"] = self.token
        return self._req("POST", base + path, data=data, files=files)


def numero_max_por_pais(meta):
    """Maior número já usado em cada país (fim do nome '... - NN') — a próxima campanha continua dele."""
    mx = collections.defaultdict(int)
    for c in meta.get(f"{CONTA}/campaigns", fields="name", limit=500):
        m = re.search(r"\]\[([A-Z]{2})\]\[(\w\w)\].*- (\d+)\s*$", c["name"])
        if m:
            mx[m.group(1)] = max(mx[m.group(1)], int(m.group(3)))
    return mx


def publicos_modelo(meta, paises):
    """Público de cada país = o do conjunto mais recente daquele país nesse modelo (mantém região/idiomas que já
    foram ajustados, ex.: Canadá só Quebec). País sem histórico usa o público padrão."""
    tpl = {}
    modelo = f"[{CFG.get('modelo', 'direto')}]"
    rows = meta.get(f"{CONTA}/adsets", fields="campaign{name},targeting,attribution_spec,created_time", limit=200)
    for a in sorted(rows, key=lambda a: a["created_time"]):
        n = a["campaign"]["name"]
        m = re.search(r"\]\[([A-Z]{2})\]\[(\w\w)\]", n)
        if m and modelo in n and "[trafego]" not in n and "[engajamento]" not in n:
            tpl[m.group(1)] = {"targeting": a["targeting"], "attribution_spec": a["attribution_spec"]}
    for p in paises:
        if p not in tpl:
            tpl[p] = {"targeting": {"geo_locations": {"countries": [p], "location_types": ["home", "recent"]},
                                    "age_min": 18, "age_max": 65, "device_platforms": ["mobile"],
                                    "publisher_platforms": ["facebook", "instagram"],
                                    "facebook_positions": ["feed", "story", "facebook_reels"],
                                    "instagram_positions": ["stream", "story", "reels", "profile_feed", "ig_search"]},
                      "attribution_spec": [{"event_type": "CLICK_THROUGH", "window_days": 7},
                                           {"event_type": "VIEW_THROUGH", "window_days": 1},
                                           {"event_type": "ENGAGED_VIDEO_VIEW", "window_days": 1}]}
            print(f"  ⚠ {p}: sem conjunto anterior na conta — usando público padrão (18-65, celular, FB+IG)")
    return tpl


def criativos_existentes(meta):
    """nome do anúncio → {idioma: video_data} usando o anúncio mais recente com esse nome."""
    idx = collections.defaultdict(dict)
    ads = meta.get(f"{CONTA}/ads", fields="name,created_time,campaign{name},creative{object_story_spec,asset_feed_spec}",
                   limit=50)
    for a in sorted(ads, key=lambda a: a["created_time"]):
        m = re.search(r"\]\[[A-Z]{2}\]\[(\w\w)\]", a["campaign"]["name"])
        oss = a["creative"].get("object_story_spec", {})
        if not m or "video_data" not in oss:
            continue
        vd, af = oss["video_data"], a["creative"].get("asset_feed_spec") or {}
        idx[a["name"]][m.group(1)] = {
            "video_id": vd["video_id"], "image_hash": vd.get("image_hash"),
            "image_url": None if vd.get("image_hash") else vd.get("image_url"),
            "message": vd.get("message") or (af.get("bodies") or [{}])[0].get("text", ""),
            "title": vd.get("title") or (af.get("titles") or [{}])[0].get("text"),
            "desc": vd.get("link_description") or (af.get("descriptions") or [{}])[0].get("text")}
    return idx


def dof_opt_out(meta):
    """Copia o degrees_of_freedom_spec (tudo OPT_OUT, sem melhorias automáticas do Advantage+ criativo)
    de um criativo recente da conta — a lista de chaves válidas muda com a API."""
    for a in meta.get(f"{CONTA}/ads", fields="creative{degrees_of_freedom_spec}", limit=5):
        spec = a["creative"].get("degrees_of_freedom_spec", {}).get("creative_features_spec")
        if spec:
            return {"creative_features_spec": spec}
    return None


def subir_video(meta, caminho, nome):
    with open(caminho, "rb") as fh:
        vid = meta.post(f"{CONTA}/advideos", {"name": nome}, base=GV,
                        files={"source": (Path(caminho).name, fh, "video/mp4")})["id"]
    for _ in range(120):  # espera ficar ready (evita posicionamento limitado) e pega a thumbnail
        d = meta.get(vid, fields="status,thumbnails{uri,is_preferred}")
        if d.get("status", {}).get("video_status") == "ready" and d.get("thumbnails"):
            th = d["thumbnails"]["data"]
            return vid, ([t for t in th if t.get("is_preferred")] or th)[0]["uri"]
        time.sleep(5)
    sys.exit(f"✗ Vídeo {caminho} não ficou pronto.")


def resolver_criativo(cr, idioma, idx):
    """String = anúncio que já existe na conta; objeto = vídeo novo {video, titulo, texto, nome?}."""
    if isinstance(cr, str):
        if cr not in idx or idioma not in idx[cr]:
            sys.exit(f"✗ Criativo '{cr}' não encontrado em campanha [{idioma}] na conta.")
        return cr, dict(idx[cr][idioma])
    nome = cr.get("nome") or Path(cr["video"]).stem[:60]
    if not Path(cr["video"]).exists():
        sys.exit(f"✗ Vídeo não existe: {cr['video']}")
    return nome, {"novo": cr["video"], "message": cr["texto"], "title": cr.get("titulo"), "desc": cr.get("descricao")}


def nome_campanha(data, c, pais, nn, extras):
    idioma, continente = PAISES[pais][0], PAISES[pais][1]
    blocos = "".join(f"[{b}]" for b in extras if b)
    return CFG.get("nome", NOME_PADRAO).format(
        data=data, modelo=CFG.get("modelo", "direto"), blocos=blocos, continente=continente, pais=pais, idioma=idioma,
        nicho=c["nicho"], site=CFG["site"], pagina_slug=CFG["pagina_slug"], nn=f"{nn:02d}")


def utm_campanha(pais, idioma, nn):
    return CFG.get("utm", UTM_PADRAO).format(utm_prefixo=CFG["utm_prefixo"], idioma=idioma, pais=pais,
                                             pais_min=pais.lower(), pagina_slug=CFG["pagina_slug"], nn=f"{nn:02d}")


def conferir(meta, log):
    st, ruins = collections.Counter(), []
    for c in log:
        d = meta.get(c["campaign_id"], fields="name,effective_status,daily_budget,adsets{ad_set_goal,promoted_object,"
                                               "targeting{targeting_automation}},ads{effective_status}")
        a = d["adsets"]["data"][0]
        st["campanha " + d["effective_status"]] += 1
        for ad in d["ads"]["data"]:
            st["anúncio " + ad["effective_status"]] += 1
        problemas = []
        if (a.get("ad_set_goal") or {}).get("type") != 0:
            problemas.append("ciclo de vida vazio")
        if a["targeting"].get("targeting_automation", {}).get("advantage_audience") != 1:
            problemas.append("advantage_audience off")
        if a["promoted_object"].get("custom_event_str") != c["evento"]:
            problemas.append("evento errado")
        if problemas:
            ruins.append((d["name"], problemas))
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
    ap.add_argument("--config", default=str(SKILL_DIR / "config.json"))
    args = ap.parse_args()
    carregar_config(args.config)
    plano = json.load(open(args.plano, encoding="utf-8"))
    token = os.getenv("META_ACCESS_TOKEN") or sys.exit("✗ META_ACCESS_TOKEN ausente no .env")
    meta = Meta(token)

    log_path = Path(args.plano).with_suffix(".log.json")
    log = json.load(open(log_path, encoding="utf-8")) if log_path.exists() else []
    if args.conferir:
        return conferir(meta, log)

    evento = plano.get("evento", CFG.get("evento_padrao", "ad_click"))
    funil = plano.get("funil", next(iter(CFG["funis"])))
    if not plano.get("url") and funil not in CFG["funis"]:
        sys.exit(f"✗ Funil '{funil}' não existe no config (tem: {', '.join(CFG['funis'])}).")
    orcamento = int(round(float(plano.get("orcamento", CFG.get("orcamento_padrao", 5))) * 100))
    inicio = plano.get("inicio", "agora")  # "agora" = ACTIVE na hora; "amanha" = agenda 00:01 do dia seguinte
    data = plano.get("data") or (datetime.now() + timedelta(days=1 if inicio == "amanha" else 0)).strftime("%d/%m")
    blocos = [b for b in plano.get("blocos", []) if b != "teste"]  # blocos extras no nome, ex.: ["pv2"]
    campanhas = plano["campanhas"]

    # regra: mesmo criativo não repete em duas campanhas do mesmo país
    if not plano.get("permitir_repetir"):
        vistos = collections.defaultdict(set)
        for c in campanhas:
            for cr in c["criativos"]:
                k = cr if isinstance(cr, str) else cr["video"]
                if k in vistos[c["pais"]]:
                    sys.exit(f"✗ '{k}' repete no país {c['pais']}. Troque ou use \"permitir_repetir\": true.")
                vistos[c["pais"]].add(k)
    for c in campanhas:
        if c["pais"] not in PAISES:
            sys.exit(f"✗ País {c['pais']} não cadastrado em \"paises\" no config.")

    paises = sorted({c["pais"] for c in campanhas})
    mx = numero_max_por_pais(meta)
    tpl = publicos_modelo(meta, paises)
    idx = criativos_existentes(meta)
    dof = None if args.dry_run else dof_opt_out(meta)
    feitos = {l["chave"] for l in log}
    novos_videos = {}

    print(f"Plano: {len(campanhas)} campanhas · conta {CONTA} · evento {evento} · funil {funil} · "
          f"${orcamento / 100:.0f}/dia cada · início {inicio} · ciclo de vida = todos os públicos · "
          f"Advantage+ Audience ligado\n")
    criadas = 0
    for i, c in enumerate(campanhas):
        chave = f"{i}:{c['pais']}"
        if chave in feitos:
            continue
        pais = c["pais"]
        idioma, _, nome_pais, primeira = PAISES[pais]
        mx[pais] += 1
        nn = mx[pais]
        fase = c.get("fase", "teste" if c["nicho"] != "Mix" else None)
        bloco_funil = CFG.get("bloco_funil", {}).get(funil)  # ex.: {"chat": "chat"} → [chat] no nome
        nome = nome_campanha(data, c, pais, nn, [bloco_funil, fase, *blocos])
        exibicao = plano.get("url") or CFG["funis"][funil].format(idioma=idioma)
        link = f"{exibicao}?utm_source=facebook&utm_campaign={utm_campanha(pais, idioma, nn)}"
        crs = [resolver_criativo(cr, idioma, idx) for cr in c["criativos"]]
        print(f"{nome}\n   {', '.join(n for n, _ in crs)}\n   {link}")
        if args.dry_run:
            continue

        status = "ACTIVE"
        camp = meta.post(f"{CONTA}/campaigns", {
            "name": nome, "objective": "OUTCOME_SALES", "status": status, "special_ad_categories": [],
            "daily_budget": orcamento, "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "is_adset_budget_sharing_enabled": "false"})["id"]
        conj = {
            "name": f"Aberto - {nome_pais}", "campaign_id": camp, "status": status,
            "optimization_goal": "OFFSITE_CONVERSIONS", "billing_event": "IMPRESSIONS", "destination_type": "WEBSITE",
            "targeting": {**tpl[pais]["targeting"], "targeting_automation": {"advantage_audience": 1}},
            "attribution_spec": tpl[pais]["attribution_spec"],
            "ad_set_goal": AD_SET_GOAL,
            "promoted_object": {"pixel_id": PIXEL, "custom_event_type": "OTHER", "custom_event_str": evento}}
        if CFG.get("dsa_beneficiario"):  # obrigatório pra países da UE
            conj["dsa_beneficiary"] = conj["dsa_payor"] = CFG["dsa_beneficiario"]
        if inicio == "amanha":
            amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            conj["start_time"] = f"{amanha}T00:01:00{CFG.get('fuso', '-0300')}"
        conjunto = meta.post(f"{CONTA}/adsets", conj)["id"]

        ids = []
        for nome_cr, s in crs:
            if "novo" in s:
                if s["novo"] not in novos_videos:
                    novos_videos[s["novo"]] = subir_video(meta, s["novo"], nome_cr)
                vid, thumb = novos_videos[s["novo"]]
                s = {**s, "video_id": vid, "image_url": thumb}
            vd = {"video_id": s["video_id"], "message": trocar_primeira_linha(s["message"], primeira),
                  "link_description": s.get("desc") or exibicao,
                  "call_to_action": {"type": "LEARN_MORE", "value": {"link": link, "link_caption": exibicao}}}
            if s.get("title"):
                vd["title"] = s["title"]
            if s.get("image_hash"):
                vd["image_hash"] = s["image_hash"]
            else:
                vd["image_url"] = s["image_url"]
            corpo = {"name": nome_cr, "object_story_spec": {"page_id": PAGINA, "video_data": vd}}
            if dof:
                corpo["degrees_of_freedom_spec"] = dof
            cr_id = meta.post(f"{CONTA}/adcreatives", corpo)["id"]
            ids.append(meta.post(f"{CONTA}/ads", {"name": nome_cr, "adset_id": conjunto,
                                                  "creative": {"creative_id": cr_id}, "status": status})["id"])

        log.append({"chave": chave, "name": nome, "link": link, "evento": evento, "campaign_id": camp,
                    "adset_id": conjunto, "ads": ids})
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
