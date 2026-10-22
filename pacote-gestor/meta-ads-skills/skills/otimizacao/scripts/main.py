#!/usr/bin/env python3
"""
otimizacao — auditoria automatizada da conta Meta Ads.

Usa os KPIs do perfil do gestor (~/.meta-ads/perfil.json): cada campanha é
julgada pela métrica do seu objetivo (CPC, CPA, CPL ou custo/engajamento).

Uso:
    python main.py
    python main.py --account act_123456789
    python main.py --date-preset last_7d --max-findings 20
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent.parent / "configurar-meta-ads" / "scripts"))

import perfil as P
from meta_api import MetaAPIError, MetaClient
from audits import estrutura as audit_estrutura
from audits import criativo as audit_criativo
from audits import publico as audit_publico
from audits import roi as audit_roi
import render


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="otimizacao",
        description="Auditoria automatizada da conta Meta Ads.",
    )
    p.add_argument("--account", help="ID da conta (act_XXXXX). Default: a do perfil")
    p.add_argument("--max-findings", type=int, default=15,
                   help="Maximo de findings priorizados (default: 15)")
    p.add_argument("--date-preset", default="last_30d",
                   help="Janela de insights (last_7d, last_14d, last_30d, last_90d). Default: last_30d")
    p.add_argument("--csv", default=None,
                   help="CSV do GAM (campanhas_*.csv). Default: o mais recente em gam_csv_dir do perfil")
    return p.parse_args()


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

    print("  Carregando custom audiences...")
    custom_audiences = client.custom_audiences()
    print(f"  {len(custom_audiences)} custom audiences")

    return {
        "account_info": account_info,
        "campaigns": campaigns,
        "adsets": adsets,
        "ads": ads,
        "insights_by_campaign": {i["campaign_id"]: i for i in insights_campaign if i.get("campaign_id")},
        "insights_by_adset": {i["adset_id"]: i for i in insights_adset if i.get("adset_id")},
        "insights_by_ad": {i["ad_id"]: i for i in insights_ad if i.get("ad_id")},
        "custom_audiences": custom_audiences,
    }


def run_audits(*, data: dict, perfil: dict, csv_path: str | None) -> tuple[list[dict], list[str], list[tuple[str, str]]]:
    findings: list[dict] = []
    skipped: list[str] = []
    errored: list[tuple[str, str]] = []
    moeda = data["account_info"].get("currency") or perfil["moeda"]

    audits = [
        ("estrutura", lambda: audit_estrutura.run(
            campaigns=data["campaigns"], adsets=data["adsets"], ads=data["ads"],
            insights_by_campaign=data["insights_by_campaign"],
            insights_by_adset=data["insights_by_adset"], perfil=perfil,
        )),
        ("criativo", lambda: audit_criativo.run(
            ads=data["ads"], adsets=data["adsets"], campaigns=data["campaigns"],
            insights_by_ad=data["insights_by_ad"], perfil=perfil, moeda=moeda,
        )),
        ("publico", lambda: audit_publico.run(
            adsets=data["adsets"], custom_audiences=data["custom_audiences"],
        )),
    ]
    if csv_path or perfil.get("gam_csv_dir"):
        audits.insert(0, ("roi", lambda: audit_roi.run(csv_path=csv_path, csv_dir=perfil.get("gam_csv_dir", ""))))
    else:
        skipped.append("roi (sem gam_csv_dir no perfil)")

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
    args = parse_args()
    perfil = P.carregar(exigir_perfil=False)
    if not P.PERFIL_PATH.exists():
        print(f"  ! Sem perfil em {P.PERFIL_PATH} — usando limites padrao.")
    account = args.account or perfil["ad_account_id"]
    if not perfil["_token"] or not account:
        print(f"Token ou conta ausentes em {P.ENV_PATH}. Rode a skill configurar-meta-ads.")
        return 2

    t0 = time.time()
    print("\n  DIAGNOSTICO DE CONTA\n")

    try:
        meta = MetaClient(access_token=perfil["_token"], ad_account_id=account,
                          api_version=perfil["api_version"])
        data = fetch_data(meta, date_preset=args.date_preset)
    except MetaAPIError as e:
        print(f"\n  ERRO Meta API: {e}")
        return 1

    print("\n  Rodando audits...")
    findings, skipped, errored = run_audits(data=data, perfil=perfil, csv_path=args.csv)

    elapsed = time.time() - t0
    print(f"\n  Total bruto: {len(findings)} findings (priorizando top {args.max_findings})")

    top = render.prioritize(findings, max_total=args.max_findings)
    print("")
    print(render.render_terminal(
        findings=top, skipped_audits=skipped, errored_audits=errored,
        account_info=data.get("account_info"), generated_at=datetime.now(),
    ))

    counts = render.summary(top)
    print(f"\n  Pronto em {elapsed:.1f}s | "
          f"{counts['alta']} criticos, {counts['media']} medios, {counts['baixa']} menores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
