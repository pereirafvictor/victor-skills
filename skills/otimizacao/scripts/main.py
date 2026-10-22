#!/usr/bin/env python3
"""
otimizacao — auditoria automatizada para arbitragem.

Uso:
    python main.py
    python main.py --account act_893607706336238
    python main.py --date-preset last_7d --max-findings 20
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from meta_api import MetaAPIError, MetaClient
from audits import estrutura as audit_estrutura
from audits import criativo as audit_criativo
from audits import publico as audit_publico
from audits import roi as audit_roi
import render


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="otimizacao",
        description="Auditoria automatizada da conta Meta Ads para arbitragem.",
    )
    p.add_argument(
        "--account",
        help="ID da conta (act_XXXXX). Se nao informado, usa META_AD_ACCOUNT_ID do .env",
    )
    p.add_argument(
        "--max-findings", type=int, default=15,
        help="Maximo de findings priorizados (default: 15)",
    )
    p.add_argument(
        "--date-preset", default="last_30d",
        help="Janela de insights (last_7d, last_14d, last_30d, last_90d). Default: last_30d",
    )
    p.add_argument(
        "--csv", default=None,
        help="Caminho do CSV do GAM (campanhas_*.csv). Se nao informado, busca o mais recente em Downloads.",
    )
    return p.parse_args()


def check_env(account_override: str | None = None) -> dict[str, str]:
    token = (os.getenv("META_ACCESS_TOKEN") or "").strip()
    account = account_override or (os.getenv("META_AD_ACCOUNT_ID") or "").strip()

    missing: list[str] = []
    if not token:
        missing.append("  - META_ACCESS_TOKEN")
    if not account:
        missing.append("  - META_AD_ACCOUNT_ID (ou use --account)")

    if missing:
        print("Variaveis de ambiente ausentes:")
        for m in missing:
            print(m)
        print("\nPreencha no .env da skill subir-campanha ou otimizacao.")
        sys.exit(2)

    return {"token": token, "account": account}


def fetch_data(client: MetaClient, *, date_preset: str) -> dict:
    print("  Carregando estrutura da conta...")
    account_info = client.account_info()
    print(f"  Conta: {account_info.get('name', '?')} ({account_info.get('currency', '?')})")

    print("  Carregando campanhas, conjuntos e anuncios...")
    campaigns = client.campaigns()
    adsets = client.adsets()
    ads = client.ads()
    print(f"  {len(campaigns)} campanhas | {len(adsets)} conjuntos | {len(ads)} anuncios")

    print(f"  Carregando insights ({date_preset})...")
    insights_campaign = client.insights(level="campaign", date_preset=date_preset)
    insights_adset = client.insights(level="adset", date_preset=date_preset)
    insights_ad = client.insights(level="ad", date_preset=date_preset)

    insights_by_campaign = {i.get("campaign_id"): i for i in insights_campaign if i.get("campaign_id")}
    insights_by_adset = {i.get("adset_id"): i for i in insights_adset if i.get("adset_id")}
    insights_by_ad = {i.get("ad_id"): i for i in insights_ad if i.get("ad_id")}

    print("  Carregando custom audiences...")
    custom_audiences = client.custom_audiences()
    print(f"  {len(custom_audiences)} custom audiences")

    return {
        "account_info": account_info,
        "campaigns": campaigns,
        "adsets": adsets,
        "ads": ads,
        "insights_by_campaign": insights_by_campaign,
        "insights_by_adset": insights_by_adset,
        "insights_by_ad": insights_by_ad,
        "custom_audiences": custom_audiences,
    }


def run_audits(*, data: dict, csv_path: str | None = None) -> tuple[list[dict], list[str], list[tuple[str, str]]]:
    findings: list[dict] = []
    skipped: list[str] = []
    errored: list[tuple[str, str]] = []

    audits = [
        (
            "roi",
            lambda: audit_roi.run(csv_path=csv_path),
        ),
        (
            "estrutura",
            lambda: audit_estrutura.run(
                campaigns=data["campaigns"],
                adsets=data["adsets"],
                ads=data["ads"],
                insights_by_campaign=data["insights_by_campaign"],
                insights_by_adset=data["insights_by_adset"],
            ),
        ),
        (
            "criativo",
            lambda: audit_criativo.run(
                ads=data["ads"],
                adsets=data["adsets"],
                insights_by_ad=data["insights_by_ad"],
                insights_by_adset=data["insights_by_adset"],
            ),
        ),
        (
            "publico",
            lambda: audit_publico.run(
                adsets=data["adsets"],
                custom_audiences=data["custom_audiences"],
            ),
        ),
    ]

    for name, fn in audits:
        print(f"  Rodando audit `{name}`...")
        try:
            result = fn()
            findings.extend(result or [])
            print(f"    {len(result or [])} findings")
        except Exception as e:
            errored.append((name, str(e)))
            print(f"    ERRO: {e}")

    return findings, skipped, errored


def main() -> int:
    # Carrega .env: primeiro da propria skill, depois da subir-campanha
    load_dotenv(SCRIPT_DIR.parent / ".env")
    subir_env = SCRIPT_DIR.parent.parent / "subir-campanha" / ".env"
    if subir_env.exists():
        load_dotenv(subir_env, override=False)

    args = parse_args()
    env = check_env(args.account)

    t0 = time.time()
    print("")
    print("  DIAGNOSTICO DE CONTA")
    print("")

    try:
        meta = MetaClient(
            access_token=env["token"],
            ad_account_id=env["account"],
        )
        data = fetch_data(meta, date_preset=args.date_preset)
    except MetaAPIError as e:
        print(f"\n  ERRO Meta API: {e}")
        return 1

    print("\n  Rodando audits...")
    findings, skipped, errored = run_audits(data=data, csv_path=args.csv)

    elapsed = time.time() - t0
    print(f"\n  Total bruto: {len(findings)} findings (priorizando top {args.max_findings})")

    now = datetime.now()
    output = render.render_terminal(
        findings=render.prioritize(findings, max_total=args.max_findings),
        skipped_audits=skipped,
        errored_audits=errored,
        account_info=data.get("account_info"),
        generated_at=now,
    )

    print("")
    print(output)

    counts = render.summary(render.prioritize(findings, max_total=args.max_findings))
    print(f"\n  Pronto em {elapsed:.1f}s | "
          f"{counts['alta']} criticos, {counts['media']} medios, {counts['baixa']} menores")

    return 0


if __name__ == "__main__":
    sys.exit(main())
