"""
subir-campanha — Victor Skills
Sobe campanha de tráfego no Meta Ads para blogs de arbitragem.
"""

import argparse
import json
import os
import sys
from datetime import date

import requests
from dotenv import load_dotenv

load_dotenv()

BLOGS = {
    "portaldoplayer": "portaldoplayer.com",
    "universodolook": "universodolook.com",
}

API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"


def get_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        print(f"✗ Variáveis ausentes no .env: {key}")
        sys.exit(1)
    return value


def build_structure(blog: str, budget: int, page_id: str | None, mode: str) -> dict:
    domain = BLOGS[blog]
    today = date.today().isoformat()

    campaign_name = f"{blog} · TRAFFIC · {today}"
    adset_name = "BR · 25-55 · Feed+Stories"
    ad_name = "anuncio-principal"

    daily_budget_cents = budget * 100

    structure = {
        "campanha": {
            "name": campaign_name,
            "objective": "OUTCOME_TRAFFIC",
            "status": "PAUSED",
            "special_ad_categories": [],
        },
        "conjunto": {
            "name": adset_name,
            "optimization_goal": "LINK_CLICKS",
            "billing_event": "IMPRESSIONS",
            "daily_budget": daily_budget_cents,
            "targeting": {
                "geo_locations": {"countries": ["BR"]},
                "age_min": 25,
                "age_max": 55,
                "publisher_platforms": ["facebook"],
                "facebook_positions": ["feed", "story"],
            },
            "status": "PAUSED",
        },
        "anuncio": {
            "name": ad_name,
            "status": "PAUSED",
            "nota": f"Sem creative_id — anexe o criativo manualmente no Ads Manager. URL destino: https://{domain}",
        },
        "meta": {
            "blog": blog,
            "dominio": domain,
            "budget_diario": f"R${budget}",
            "modo": mode,
            "data": today,
        },
    }

    if page_id:
        structure["conjunto"]["page_id"] = page_id

    return structure


def dry_run(structure: dict):
    print("\n=== DRY-RUN — nada será criado ===\n")
    print(json.dumps(structure, indent=2, ensure_ascii=False))
    print("\n==================================")
    print(f"Blog:          {structure['meta']['blog']} ({structure['meta']['dominio']})")
    print(f"Budget diário: {structure['meta']['budget_diario']}")
    print(f"Modo:          {structure['meta']['modo']}")
    print(f"Status:        PAUSED (ativar manualmente no Ads Manager)")
    print("==================================\n")


def create_campaign(account_id: str, token: str, structure: dict) -> str:
    url = f"{BASE_URL}/{account_id}/campaigns"
    payload = {**structure["campanha"], "access_token": token}
    r = requests.post(url, data=payload)
    r.raise_for_status()
    return r.json()["id"]


def create_adset(account_id: str, token: str, campaign_id: str, structure: dict) -> str:
    url = f"{BASE_URL}/{account_id}/adsets"
    payload = {
        **structure["conjunto"],
        "campaign_id": campaign_id,
        "targeting": json.dumps(structure["conjunto"]["targeting"]),
        "access_token": token,
    }
    payload.pop("targeting", None)
    payload["targeting"] = json.dumps(structure["conjunto"]["targeting"])
    r = requests.post(url, data=payload)
    r.raise_for_status()
    return r.json()["id"]


def create_ad(account_id: str, token: str, adset_id: str, structure: dict) -> str:
    url = f"{BASE_URL}/{account_id}/ads"
    payload = {
        "name": structure["anuncio"]["name"],
        "adset_id": adset_id,
        "status": "PAUSED",
        "access_token": token,
    }
    r = requests.post(url, data=payload)
    r.raise_for_status()
    return r.json()["id"]


def ads_manager_link(account_id: str) -> str:
    numeric_id = account_id.replace("act_", "")
    return f"https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={numeric_id}"


def main():
    parser = argparse.ArgumentParser(description="Sobe campanha de tráfego no Meta Ads")
    parser.add_argument("--blog", required=True, choices=list(BLOGS.keys()), help="Blog de destino")
    parser.add_argument("--budget", required=True, type=int, help="Budget diário em reais")
    parser.add_argument("--page-id", default=None, help="ID da página do Facebook (opcional)")
    parser.add_argument("--abo", action="store_true", default=True, help="Orçamento por conjunto (default)")
    parser.add_argument("--cbo", action="store_true", help="Orçamento na campanha")
    parser.add_argument("--dry-run", action="store_true", help="Mostra estrutura sem criar nada")
    args = parser.parse_args()

    mode = "CBO" if args.cbo else "ABO"
    structure = build_structure(args.blog, args.budget, args.page_id, mode)

    if args.dry_run:
        dry_run(structure)
        return

    token = get_env("META_ACCESS_TOKEN")
    account_id = get_env("META_AD_ACCOUNT_ID")

    print(f"\nSubindo campanha para {args.blog}...")

    try:
        campaign_id = create_campaign(account_id, token, structure)
        print(f"✓ Campanha criada: {campaign_id}")

        adset_id = create_adset(account_id, token, campaign_id, structure)
        print(f"✓ Conjunto criado: {adset_id}")

        ad_id = create_ad(account_id, token, adset_id, structure)
        print(f"✓ Anúncio criado: {ad_id}")

        print(f"\n✓ Campanha PAUSED criada com sucesso.")
        print(f"→ Revise e ative no Ads Manager:")
        print(f"  {ads_manager_link(account_id)}\n")

    except requests.HTTPError as e:
        print(f"\n✗ Erro na API do Meta: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
