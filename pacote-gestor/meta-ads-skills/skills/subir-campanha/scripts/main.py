"""
subir-campanha — sobe campanha no Meta Ads a partir do perfil do gestor.

Estrutura padrão: 1 campanha × N conjuntos × M anúncios (perfil.json → estrutura).
Objetivos: trafego | vendas | leads | engajamento.
Sempre cria tudo PAUSED.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent / "configurar-meta-ads" / "scripts"))
import perfil as P  # noqa: E402

OBJETIVOS = {
    "trafego": {
        "objective": "OUTCOME_TRAFFIC",
        "optimization_goal": "LINK_CLICKS",
        "destination_type": "WEBSITE",
        "rotulo": "TRAFEGO",
    },
    "vendas": {
        "objective": "OUTCOME_SALES",
        "optimization_goal": "OFFSITE_CONVERSIONS",
        "destination_type": "WEBSITE",
        "precisa_pixel": True,
        "rotulo": "VENDAS",
    },
    "leads": {
        "objective": "OUTCOME_LEADS",
        "optimization_goal": "OFFSITE_CONVERSIONS",
        "destination_type": "WEBSITE",
        "precisa_pixel": True,
        "evento": "LEAD",
        "rotulo": "LEADS",
    },
    "engajamento": {
        "objective": "OUTCOME_ENGAGEMENT",
        "optimization_goal": "POST_ENGAGEMENT",
        "destination_type": "ON_POST",
        "rotulo": "ENGAJAMENTO",
    },
}

EU_COUNTRIES = {"AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU",
                "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"}

VIDEO_EXT = {".mp4", ".mov"}
IMAGE_EXT = {".jpg", ".jpeg", ".png"}

TEXTO_PADRAO = {
    "pt": "Descubra mais clicando no link!",
    "es": "¡Descubre más haciendo clic en el enlace!",
    "fr": "Découvrez-en plus en cliquant sur le lien !",
    "en": "Find out more by clicking the link!",
}


def fail(msg: str, code: int = 1):
    print(f"✗ {msg}")
    sys.exit(code)


def build_targeting(cfg: dict, paises: list[str], advantage_plus: bool) -> dict:
    pub = cfg["publico"]
    t: dict = {"geo_locations": {"countries": paises}}
    if advantage_plus:
        t["targeting_automation"] = {"advantage_audience": 1}
        return t
    t["age_min"] = pub["idade_min"]
    t["age_max"] = pub["idade_max"]
    t["targeting_automation"] = {"advantage_audience": 0}
    for k, v in (pub.get("posicionamentos") or {}).items():
        if v:
            t[k] = v
    return t


def posicionamento_label(cfg: dict, advantage_plus: bool) -> str:
    if advantage_plus:
        return "Advantage+"
    plats = (cfg["publico"].get("posicionamentos") or {}).get("publisher_platforms") or []
    return "+".join(p[:2].upper() for p in plats) or "Auto"


def listar_criativos(pasta: str | None) -> list[Path]:
    if not pasta:
        return []
    d = Path(pasta)
    if not d.is_dir():
        fail(f"Pasta de criativos não existe: {pasta}")
    return sorted(p for p in d.iterdir() if p.suffix.lower() in VIDEO_EXT | IMAGE_EXT)


def build_structure(args, cfg: dict) -> dict:
    obj = OBJETIVOS[args.objetivo]
    pagina = P.achar(cfg["paginas"], args.pagina)
    if not pagina:
        nomes = ", ".join(p.get("apelido") or p.get("nome") for p in cfg["paginas"]) or "(nenhuma)"
        motivo = f"Página não encontrada: '{args.pagina}'." if args.pagina else "Informe --pagina."
        fail(f"{motivo} Páginas do perfil: {nomes}", 2)

    destino = P.achar(cfg["destinos"], args.destino) if not args.url else None
    if args.url:
        url, paises, idioma = args.url, [], "pt"
    elif destino:
        url, paises, idioma = destino["url"], destino.get("paises") or [], destino.get("idioma", "pt")
    else:
        nomes = ", ".join(d.get("apelido", d.get("url")) for d in cfg["destinos"]) or "(nenhum)"
        motivo = f"Destino não encontrado: '{args.destino}'." if args.destino else "Informe --destino."
        fail(f"{motivo} Destinos do perfil: {nomes}. Ou use --url.", 2)
    if args.pais:
        paises = [p.strip().upper() for p in args.pais.split(",")]
    if not paises:
        fail("Sem país: informe --pais (ex: BR) ou cadastre 'paises' no destino.", 2)

    evento = args.evento or obj.get("evento") or cfg["evento_conversao"]
    pixel = args.pixel or cfg["pixel_id"]
    if obj.get("precisa_pixel") and not pixel:
        fail(f"Objetivo '{args.objetivo}' precisa de pixel: cadastre pixel_id no perfil ou use --pixel.", 2)

    estrutura = cfg["estrutura"]
    n_conj = args.conjuntos or estrutura["conjuntos"]
    n_ads = args.anuncios or estrutura["anuncios_por_conjunto"]
    adv = args.advantage_plus or cfg["publico"].get("advantage_plus", False)
    targeting = build_targeting(cfg, paises, adv)
    hoje = date.today().isoformat()
    pais_label = "+".join(paises)
    pub = cfg["publico"]
    idade = "Adv+" if adv else f"{pub['idade_min']}-{pub['idade_max']}"

    texto = args.texto or cfg["textos"].get(idioma) or TEXTO_PADRAO.get(idioma, TEXTO_PADRAO["pt"])
    nome_base = args.nome or (destino or {}).get("apelido") or pagina.get("apelido") or "campanha"

    adset_base = {
        "optimization_goal": args.otimizacao or obj["optimization_goal"],
        "billing_event": "IMPRESSIONS",
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "daily_budget": int(round(args.budget * 100)),
        "destination_type": obj["destination_type"],
        "targeting": targeting,
        "status": "PAUSED",
    }
    if obj.get("precisa_pixel"):
        adset_base["promoted_object"] = {"pixel_id": pixel, "custom_event_type": evento}
    elif obj["destination_type"] == "ON_POST":
        adset_base["promoted_object"] = {"page_id": pagina["id"]}
    if paises[0] in EU_COUNTRIES:
        dsa = cfg["dsa_beneficiario"] or pagina.get("nome") or pagina.get("apelido")
        adset_base["dsa_beneficiary"] = dsa
        adset_base["dsa_payor"] = dsa

    conjuntos = []
    for i in range(1, n_conj + 1):
        sufixo = f" · {i:02d}" if n_conj > 1 else ""
        conjuntos.append({**adset_base, "name": f"{pais_label} · {idade} · {posicionamento_label(cfg, adv)}{sufixo}"})

    return {
        "campanha": {
            "name": f"{nome_base} · {obj['rotulo']} · {hoje}",
            "objective": obj["objective"],
            "status": "PAUSED",
            "special_ad_categories": [],
            "buying_type": "AUCTION",
            "is_adset_budget_sharing_enabled": False,
        },
        "conjuntos": conjuntos,
        "anuncios_por_conjunto": n_ads,
        "pagina": pagina,
        "url": url,
        "paises": paises,
        "texto": texto,
        "evento": evento if obj.get("precisa_pixel") else None,
        "pixel": pixel if obj.get("precisa_pixel") else None,
        "advantage_plus": adv,
        "budget_total": args.budget * n_conj,
    }


def dry_run(s: dict, criativos: list[Path], cfg: dict):
    moeda = cfg["moeda"]
    c = s["campanha"]
    print("\n=== DRY-RUN — nada será criado ===\n")
    print(f"Conta:            {cfg['ad_account_id'] or '(não configurada)'}")
    print(f"Campanha:         {c['name']}")
    print(f"Objetivo:         {c['objective']}  (otimização: {s['conjuntos'][0]['optimization_goal']})")
    if s["pixel"]:
        print(f"Pixel / evento:   {s['pixel']} / {s['evento']}")
    print(f"Página:           {s['pagina'].get('nome') or s['pagina'].get('apelido')} ({s['pagina']['id']})")
    print(f"Destino:          {s['url']}")
    if cfg["utm"]:
        print(f"UTM:              {cfg['utm']}")
    print(f"Países:           {', '.join(s['paises'])}")
    print(f"Advantage+:       {'Sim' if s['advantage_plus'] else 'Não'}")
    print(f"Budget/conjunto:  {s['conjuntos'][0]['daily_budget'] / 100:.2f} {moeda}/dia")
    print(f"Budget total:     {s['budget_total']:.2f} {moeda}/dia")
    print(f"Texto:            {s['texto']}")
    print(f"\nConjuntos ({len(s['conjuntos'])}) × anúncios ({s['anuncios_por_conjunto']}):")
    for conj in s["conjuntos"]:
        print(f"  • {conj['name']}")
        for j in range(s["anuncios_por_conjunto"]):
            nome = criativos[j].name if j < len(criativos) else "(sem criativo)"
            print(f"      anuncio-{j + 1:02d} → {nome}")
    if len(criativos) < s["anuncios_por_conjunto"]:
        print(f"\n! Só {len(criativos)} criativo(s) na pasta para {s['anuncios_por_conjunto']} anúncios por conjunto.")
    print("\nStatus: PAUSED (ativar manualmente no Ads Manager)")
    print("==================================\n")


class Meta:
    def __init__(self, cfg: dict):
        self.token = cfg["_token"]
        self.conta = cfg["ad_account_id"]
        self.base = f"https://graph.facebook.com/{cfg['api_version']}"

    def post(self, path: str, data: dict, files=None) -> dict:
        payload = {k: (json.dumps(v) if isinstance(v, (dict, list, bool)) else v) for k, v in data.items()}
        payload["access_token"] = self.token
        r = requests.post(f"{self.base}/{path}", data=payload, files=files, timeout=300)
        resp = r.json()
        if "error" in resp:
            e = resp["error"]
            msg = e.get("error_user_msg") or e.get("message")
            raise RuntimeError(f"{path}: {msg}")
        return resp

    def get(self, path: str, **params) -> dict:
        params["access_token"] = self.token
        return requests.get(f"{self.base}/{path}", params=params, timeout=60).json()


def subir_criativo(meta: Meta, arquivo: Path) -> dict:
    print(f"    ↑ Enviando {arquivo.name} ...", end=" ", flush=True)
    with open(arquivo, "rb") as f:
        if arquivo.suffix.lower() in IMAGE_EXT:
            resp = meta.post(f"{meta.conta}/adimages", {}, files={"filename": (arquivo.name, f)})
            img = next(iter(resp["images"].values()))
            print(f"✓ imagem {img['hash'][:10]}")
            return {"tipo": "imagem", "hash": img["hash"]}
        resp = meta.post(f"{meta.conta}/advideos", {"title": arquivo.stem}, files={"source": f})
    vid = resp["id"]
    thumb = None
    for _ in range(12):  # thumbnail demora alguns segundos
        time.sleep(5)
        thumb = meta.get(vid, fields="picture").get("picture")
        if thumb:
            break
    print(f"✓ vídeo {vid}")
    return {"tipo": "video", "id": vid, "thumb": thumb}


def criar_creative(meta: Meta, midia: dict, s: dict, cfg: dict, nome: str) -> str:
    cta = {"type": cfg["cta"], "value": {"link": s["url"]}}
    if midia["tipo"] == "video":
        story = {"page_id": s["pagina"]["id"], "video_data": {
            "video_id": midia["id"], "message": s["texto"], "call_to_action": cta,
            **({"image_url": midia["thumb"]} if midia["thumb"] else {}),
        }}
    else:
        story = {"page_id": s["pagina"]["id"], "link_data": {
            "image_hash": midia["hash"], "link": s["url"], "message": s["texto"], "call_to_action": cta,
        }}
    data = {"name": nome, "object_story_spec": story}
    if cfg["utm"]:
        data["url_tags"] = cfg["utm"]
    return meta.post(f"{meta.conta}/adcreatives", data)["id"]


def ads_manager_link(conta: str) -> str:
    return f"https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={conta.replace('act_', '')}"


def main():
    cfg = P.carregar()
    ap = argparse.ArgumentParser(description="Sobe campanha no Meta Ads (sempre PAUSED)")
    ap.add_argument("--budget", required=True, type=float, help="Budget diário POR CONJUNTO, na moeda da conta")
    ap.add_argument("--objetivo", choices=list(OBJETIVOS), default=cfg["objetivo_padrao"])
    ap.add_argument("--pagina", default=None, help="Apelido, nome ou ID da página (do perfil)")
    ap.add_argument("--destino", default=None, help="Apelido do destino (do perfil)")
    ap.add_argument("--url", default=None, help="URL de destino avulsa (ignora --destino)")
    ap.add_argument("--pais", default=None, help="País(es) alvo, ex: BR ou ES,PT")
    ap.add_argument("--criativos", default=None, help="Pasta com vídeos (.mp4/.mov) e/ou imagens (.jpg/.png)")
    ap.add_argument("--conjuntos", type=int, default=None)
    ap.add_argument("--anuncios", type=int, default=None, help="Anúncios por conjunto")
    ap.add_argument("--texto", default=None, help="Texto principal do anúncio")
    ap.add_argument("--nome", default=None, help="Prefixo do nome da campanha")
    ap.add_argument("--pixel", default=None)
    ap.add_argument("--evento", default=None, help="Evento de conversão (PURCHASE, LEAD, COMPLETE_REGISTRATION...)")
    ap.add_argument("--otimizacao", default=None, help="Sobrescreve optimization_goal (ex: LANDING_PAGE_VIEWS, THRUPLAY)")
    ap.add_argument("--advantage-plus", action="store_true")
    ap.add_argument("--forcar", action="store_true", help="Ignora o teto orcamento_max_diario do perfil")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    s = build_structure(args, cfg)
    criativos = listar_criativos(args.criativos)

    teto = cfg["orcamento_max_diario"]
    if teto and s["budget_total"] > teto and not args.forcar:
        fail(f"Budget total {s['budget_total']:.2f} passa do teto do perfil ({teto}). Use --forcar se for isso mesmo.", 2)

    if args.dry_run:
        dry_run(s, criativos, cfg)
        return

    if not cfg["_token"] or not cfg["ad_account_id"]:
        fail(f"Token ou conta ausentes em {P.ENV_PATH}. Rode a skill configurar-meta-ads.", 2)
    if not criativos:
        fail("Nenhum criativo encontrado. Passe --criativos com a pasta dos vídeos/imagens.", 2)

    meta = Meta(cfg)
    try:
        camp = meta.post(f"{meta.conta}/campaigns", s["campanha"])["id"]
        print(f"✓ Campanha: {camp}")

        midias = [subir_criativo(meta, a) for a in criativos[: s["anuncios_por_conjunto"]]]
        creatives = [criar_creative(meta, m, s, cfg, f"criativo-{i + 1:02d}") for i, m in enumerate(midias)]

        for conj in s["conjuntos"]:
            adset = meta.post(f"{meta.conta}/adsets", {**conj, "campaign_id": camp})["id"]
            print(f"  ✓ Conjunto: {conj['name']} ({adset})")
            for j, cr in enumerate(creatives, 1):
                ad = meta.post(f"{meta.conta}/ads", {
                    "name": f"anuncio-{j:02d}", "adset_id": adset,
                    "creative": {"creative_id": cr}, "status": "PAUSED",
                })["id"]
                print(f"    ✓ anuncio-{j:02d}: {ad}")
    except RuntimeError as e:
        fail(f"Erro na API do Meta — {e}")

    print("\n✓ Estrutura criada (PAUSED).")
    print(f"→ Revise e ative no Ads Manager:\n  {ads_manager_link(meta.conta)}\n")


if __name__ == "__main__":
    main()
