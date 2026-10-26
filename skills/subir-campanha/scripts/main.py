"""
subir-campanha — Victor Skills
Sobe campanha de tráfego no Meta Ads para blogs de arbitragem.
3 fases: teste → pre-escala → escala
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BLOGS = {
    "portaldoplayer":   {"domain": "portaldoplayer.com",    "countries": ["BR"]},
    "universodolook":   {"domain": "universodolook.com",    "countries": ["BR"]},
    "universodolook-es":{"domain": "universodolook.com/es", "countries": ["ES"]},
    "universodolook-fr":{"domain": "universodolook.com/fr", "countries": ["FR"]},
}

API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

FASE_DESC = {
    "teste":      "Valida CPC. Critério: CPC < R$0,15 em algum conjunto após 3 dias sem mexer.",
    "pre-escala": "4 cópias do conjunto campeão. Critério: CPC estável após 1 dia → duplicar.",
    "escala":     "1 conjunto com 3 cópias do criativo campeão. Roda até CPC subir.",
}

AD_COPY = {
    "BR": "Descubra as últimas tendências no nosso blog!",
    "ES": "¡Descubre las últimas tendencias en nuestra página!",
    "FR": "Découvrez les dernières tendances sur notre page !",
}


def get_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        print(f"✗ Variáveis ausentes no .env: {key}")
        sys.exit(1)
    return value


def build_targeting(advantage_plus: bool, countries: list[str]) -> dict:
    if advantage_plus:
        return {
            "geo_locations": {"countries": countries},
            "targeting_automation": {"advantage_audience": 1},
        }
    return {
        "geo_locations": {"countries": countries},
        "age_min": 25,
        "age_max": 55,
        "publisher_platforms": ["facebook"],
        "facebook_positions": ["feed", "story"],
        "targeting_automation": {"advantage_audience": 0},
    }


def build_adsets(fase: str, budget_cents: int, conjuntos: int, targeting: dict, page_id: str | None) -> list[dict]:
    base = {
        "optimization_goal": "LINK_CLICKS",
        "billing_event": "IMPRESSIONS",
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "daily_budget": budget_cents,
        "targeting": targeting,
        "status": "PAUSED",
    }
    if page_id:
        base["page_id"] = page_id

    if fase == "teste":
        return [{**base, "name": f"BR · 25-55 · Feed+Stories · {i:02d}"} for i in range(1, conjuntos + 1)]
    if fase == "pre-escala":
        return [{**base, "name": f"BR · 25-55 · Feed+Stories · Campeão · {i:02d}"} for i in range(1, 5)]
    return [{**base, "name": "BR · 25-55 · Feed+Stories · Campeão"}]


def build_structure(blog: str, budget: int, page_id: str | None, fase: str, conjuntos: int, advantage_plus: bool) -> dict:
    cfg = BLOGS[blog]
    domain = cfg["domain"]
    countries = cfg["countries"]
    today = date.today().isoformat()
    fase_label = fase.upper().replace("-", "_")
    budget_cents = budget * 100
    targeting = build_targeting(advantage_plus, countries)
    adsets = build_adsets(fase, budget_cents, conjuntos, targeting, page_id)
    ads_per_adset = 3 if fase == "escala" else 1

    return {
        "campanha": {
            "name": f"{blog} · TRAFFIC · {fase_label} · {today}",
            "objective": "OUTCOME_TRAFFIC",
            "status": "PAUSED",
            "special_ad_categories": [],
        },
        "conjuntos": adsets,
        "anuncios_por_conjunto": ads_per_adset,
        "meta": {
            "blog": blog,
            "dominio": domain,
            "countries": countries,
            "budget_por_conjunto": f"R${budget}/dia",
            "budget_total": f"R${budget * len(adsets)}/dia",
            "fase": fase,
            "n_conjuntos": len(adsets),
            "anuncios_por_conjunto": ads_per_adset,
            "advantage_plus": advantage_plus,
            "data": today,
            "descricao": FASE_DESC[fase],
        },
    }


def dry_run(structure: dict, videos: list[Path]):
    m = structure["meta"]
    print("\n=== DRY-RUN — nada será criado ===\n")
    print(f"Fase:            {m['fase'].upper()}")
    print(f"Blog:            {m['blog']} ({m['dominio']})")
    print(f"Mercado:         {', '.join(m['countries'])}")
    print(f"Budget/conjunto: {m['budget_por_conjunto']}")
    print(f"Conjuntos:       {m['n_conjuntos']}")
    print(f"Budget total:    {m['budget_total']}")
    print(f"Advantage+:      {'Sim' if m['advantage_plus'] else 'Não'}")
    print(f"\nCampanha: {structure['campanha']['name']}")
    print("\nConjuntos + criativos:")
    for i, adset in enumerate(structure["conjuntos"], 1):
        video = videos[i - 1].name if i <= len(videos) else "(sem vídeo)"
        print(f"  {i}. {adset['name']}  →  {video}")
    print(f"\n→ {m['descricao']}")
    print(f"\nStatus: PAUSED (ativar manualmente no Ads Manager)")
    print("==================================\n")


def upload_video(account_id: str, token: str, video_path: Path) -> tuple[str, str | None]:
    import time
    print(f"    ↑ Enviando vídeo: {video_path.name} ...", end=" ", flush=True)
    with open(video_path, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/{account_id}/advideos",
            data={"title": video_path.stem, "access_token": token},
            files={"source": f},
        )
    r.raise_for_status()
    vid_id = r.json()["id"]
    print(f"✓ {vid_id}")
    # Aguarda thumbnail gerada pelo Meta
    time.sleep(5)
    r2 = requests.get(f"{BASE_URL}/{vid_id}?fields=picture&access_token={token}")
    picture_url = r2.json().get("picture") if r2.ok else None
    return vid_id, picture_url


def create_video_creative(account_id: str, token: str, video_id: str, page_id: str, domain: str, country: str, name: str, page_name: str = "", thumbnail_url: str | None = None) -> str:
    copy = AD_COPY.get(country, AD_COPY["BR"])
    link = f"https://{domain}" if not domain.startswith("http") else domain
    video_data: dict = {
        "video_id": video_id,
        "message": copy,
        "call_to_action": {
            "type": "LEARN_MORE",
            "value": {"link": link},
        },
    }
    if thumbnail_url:
        video_data["image_url"] = thumbnail_url
    object_story_spec = {
        "page_id": page_id,
        "video_data": video_data,
    }
    payload = {
        "name": name,
        "object_story_spec": json.dumps(object_story_spec),
        "access_token": token,
    }
    # DSA obrigatório para países da UE
    EU_COUNTRIES = {"AT","BE","BG","CY","CZ","DE","DK","EE","ES","FI","FR","GR","HR","HU","IE","IT","LT","LU","LV","MT","NL","PL","PT","RO","SE","SI","SK"}

    if country.upper() in EU_COUNTRIES:
        beneficiary = page_name or name
        payload["dsa_beneficiary"] = beneficiary
        payload["dsa_payor"] = beneficiary
    r = requests.post(f"{BASE_URL}/{account_id}/adcreatives", data=payload)
    r.raise_for_status()
    return r.json()["id"]


def ads_manager_link(account_id: str) -> str:
    numeric_id = account_id.replace("act_", "")
    return f"https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={numeric_id}"


def main():
    parser = argparse.ArgumentParser(description="Sobe campanha de tráfego no Meta Ads")
    parser.add_argument("--blog", required=True, choices=list(BLOGS.keys()))
    parser.add_argument("--budget", required=True, type=int, help="Budget diário por conjunto em reais")
    parser.add_argument("--fase", required=True, choices=["teste", "pre-escala", "escala"])
    parser.add_argument("--conjuntos", type=int, default=3, help="Conjuntos na fase teste (default: 3)")
    parser.add_argument("--page-id", default=None)
    parser.add_argument("--creatives-dir", default=None, help="Pasta com vídeos .mp4 (1 por conjunto na fase teste)")
    parser.add_argument("--url", default=None, help="URL de destino dos anúncios (substitui o domain do blog)")
    parser.add_argument("--country", default=None, help="País alvo ex: ES, FR, BR (substitui o do blog)")
    parser.add_argument("--page-name", default=None, help="Nome da página Facebook (usado como DSA beneficiary em países EU)")
    parser.add_argument("--advantage-plus", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Permite sobrescrever URL de destino e país alvo
    if args.url or args.country:
        cfg_override = dict(BLOGS[args.blog])
        if args.url:
            cfg_override["domain"] = args.url.replace("https://", "").replace("http://", "").rstrip("/")
        if args.country:
            cfg_override["countries"] = [args.country.upper()]
        BLOGS[args.blog] = cfg_override

    structure = build_structure(
        args.blog, args.budget, args.page_id,
        args.fase, args.conjuntos, args.advantage_plus,
    )

    videos: list[Path] = []
    if args.creatives_dir:
        videos = sorted(Path(args.creatives_dir).glob("*.mp4"))

    if args.dry_run:
        dry_run(structure, videos)
        return

    token = get_env("META_ACCESS_TOKEN")
    account_id = get_env("META_AD_ACCOUNT_ID")
    cfg = BLOGS[args.blog]

    print(f"\nSubindo campanha [{args.fase}] para {args.blog}...")

    try:
        # Campanha
        camp = structure["campanha"]
        r = requests.post(
            f"{BASE_URL}/{account_id}/campaigns",
            data={
                **{k: v for k, v in camp.items() if not isinstance(v, list)},
                "special_ad_categories": json.dumps(camp["special_ad_categories"]),
                "buying_type": "AUCTION",
                "is_adset_budget_sharing_enabled": False,
                "access_token": token,
            },
        )
        r.raise_for_status()
        campaign_id = r.json()["id"]
        print(f"✓ Campanha: {campaign_id}")

        for i, adset_def in enumerate(structure["conjuntos"], 1):
            targeting = adset_def["targeting"]
            adset_fields = {k: v for k, v in adset_def.items() if k != "targeting"}
            EU_COUNTRIES = {"AT","BE","BG","CY","CZ","DE","DK","EE","ES","FI","FR","GR","HR","HU","IE","IT","LT","LU","LV","MT","NL","PL","PT","RO","SE","SI","SK"}
            adset_payload = {**adset_fields, "campaign_id": campaign_id, "targeting": json.dumps(targeting), "access_token": token}
            if cfg["countries"][0].upper() in EU_COUNTRIES:
                dsa_name = args.page_name if hasattr(args, "page_name") and args.page_name else "Nayara Souza"
                adset_payload["dsa_beneficiary"] = dsa_name
                adset_payload["dsa_payor"] = dsa_name
            r = requests.post(f"{BASE_URL}/{account_id}/adsets", data=adset_payload)
            r.raise_for_status()
            adset_id = r.json()["id"]
            print(f"  ✓ Conjunto {i}: {adset_id}")

            # Upload vídeo + criativo + anúncio (se houver vídeo e page_id)
            if videos and args.page_id and i <= len(videos):
                video_id, thumbnail_url = upload_video(account_id, token, videos[i - 1])
                creative_id = create_video_creative(
                    account_id, token, video_id, args.page_id,
                    cfg["domain"], cfg["countries"][0],
                    f"criativo-{args.blog}-{i:02d}",
                    page_name=args.page_name or "",
                    thumbnail_url=thumbnail_url,
                )
                print(f"    ✓ Criativo: {creative_id}")

                r_ad = requests.post(
                    f"{BASE_URL}/{account_id}/ads",
                    data={
                        "name": f"anuncio-{i:02d}",
                        "adset_id": adset_id,
                        "creative": json.dumps({"creative_id": creative_id}),
                        "status": "PAUSED",
                        "access_token": token,
                    },
                )
                r_ad.raise_for_status()
                ad_resp = r_ad.json()
                if "id" in ad_resp:
                    print(f"    ✓ Anúncio: {ad_resp['id']}")
                else:
                    print(f"    ✗ Resposta inesperada do anúncio: {ad_resp}")
                    sys.exit(1)

        print(f"\n✓ Estrutura criada (PAUSED).")
        print(f"→ Revise e ative no Ads Manager:")
        print(f"  {ads_manager_link(account_id)}\n")

    except requests.HTTPError as e:
        print(f"\n✗ Erro na API do Meta: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
