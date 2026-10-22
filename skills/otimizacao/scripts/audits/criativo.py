"""
criativo.py — Auditoria de criativos para arbitragem.

KPI principal: CPC (nao CPA).

Detecta:
- CPC alto (> R$0,25) em anuncios com gasto significativo
- Fadiga criativa (frequencia > 3x + idade > 14 dias)
- Sem variacao criativa (< 3 anuncios ativos no conjunto)
- CTR baixo (< 1%) apos 1000+ impressoes
- Ranking de anuncios por CPC (identifica campeao)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

CPC_RUIM = 0.25
CPC_MEDIOCRE = 0.15
CPC_BOM = 0.10
MIN_SPEND_FOR_CPC = 10.0
MIN_IMPRESSIONS_FOR_CTR = 1000
FREQ_LIMIT = 3.0
AGE_LIMIT_DAYS = 14


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _safe_float(val: Any) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def run(
    *,
    ads: list[dict[str, Any]],
    adsets: list[dict[str, Any]],
    insights_by_ad: dict[str, dict[str, Any]],
    insights_by_adset: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    adset_map = {a["id"]: a for a in adsets if "id" in a}
    active_ads = [a for a in ads if a.get("effective_status") == "ACTIVE"]

    # 1. Anuncios com CPC alto
    high_cpc: list[tuple[str, float, float]] = []
    for ad in active_ads:
        ins = insights_by_ad.get(ad["id"])
        if not ins:
            continue
        spend = _safe_float(ins.get("spend"))
        cpc = _safe_float(ins.get("cpc"))
        if spend >= MIN_SPEND_FOR_CPC and cpc > CPC_RUIM:
            high_cpc.append((ad["name"], cpc, spend))

    high_cpc.sort(key=lambda x: x[1], reverse=True)
    if high_cpc:
        detail = ", ".join(
            f"{name} (CPC R${cpc:.2f}, gasto R${spend:.0f})"
            for name, cpc, spend in high_cpc[:5]
        )
        findings.append({
            "frente": "Criativo",
            "severity": "alta",
            "titulo": f"{len(high_cpc)} anuncios com CPC acima de R${CPC_RUIM:.2f}",
            "descricao": (
                f"Anuncios queimando budget com CPC alto demais pra arbitragem: {detail}. "
                f"Meta de CPC pra arbitragem: < R${CPC_MEDIOCRE:.2f}."
            ),
            "recomendacao": (
                "Pause os anuncios com CPC > R$0,25 e substitua por criativos novos. "
                "Se todos os 3 anuncios da campanha estao ruins, pause a campanha inteira."
            ),
        })

    # 2. Fadiga criativa (frequencia alta + idade > 14 dias)
    fatigued: list[tuple[str, float, int]] = []
    for ad in active_ads:
        ins = insights_by_ad.get(ad["id"])
        if not ins:
            continue
        freq = _safe_float(ins.get("frequency"))
        created = _parse_dt(ad.get("created_time"))
        if not created:
            continue
        age_days = (now - created).days
        if freq > FREQ_LIMIT and age_days > AGE_LIMIT_DAYS:
            fatigued.append((ad["name"], freq, age_days))

    fatigued.sort(key=lambda x: x[1], reverse=True)
    if fatigued:
        detail = ", ".join(
            f"{name} (freq {freq:.1f}x, {days}d)"
            for name, freq, days in fatigued[:5]
        )
        findings.append({
            "frente": "Criativo",
            "severity": "alta",
            "titulo": f"{len(fatigued)} anuncios com fadiga criativa",
            "descricao": (
                f"Frequencia alta + anuncio velho = publico saturado, CPC sobe. "
                f"Anuncios fatigados: {detail}."
            ),
            "recomendacao": (
                "Troque os criativos fatigados por videos novos. "
                "Na arbitragem, criativo se queima rapido — rotacione a cada 2-3 semanas."
            ),
        })

    # 3. Sem variacao criativa (< 3 anuncios ativos por conjunto)
    from collections import defaultdict
    ads_by_adset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ad in active_ads:
        ads_by_adset[ad.get("adset_id", "")].append(ad)

    low_variation: list[str] = []
    for adset_id, adset_ads in ads_by_adset.items():
        if len(adset_ads) < 3:
            adset = adset_map.get(adset_id)
            name = adset["name"] if adset else adset_id
            low_variation.append(f"{name} ({len(adset_ads)} ads)")

    if low_variation:
        findings.append({
            "frente": "Criativo",
            "severity": "media",
            "titulo": f"{len(low_variation)} conjuntos com menos de 3 anuncios",
            "descricao": (
                f"O modelo escala precisa de 3 anuncios pra identificar o campeao. "
                f"Conjuntos incompletos: {', '.join(low_variation[:5])}"
                + (f" (+{len(low_variation) - 5})" if len(low_variation) > 5 else "")
                + "."
            ),
            "recomendacao": (
                "Adicione criativos ate completar 3 por conjunto. "
                "Sem variacao nao da pra saber qual criativo performa melhor."
            ),
        })

    # 4. CTR baixo (< 1%) apos impressoes suficientes
    low_ctr: list[tuple[str, float, int]] = []
    for ad in active_ads:
        ins = insights_by_ad.get(ad["id"])
        if not ins:
            continue
        impressions = int(_safe_float(ins.get("impressions")))
        ctr = _safe_float(ins.get("ctr"))
        if impressions >= MIN_IMPRESSIONS_FOR_CTR and ctr < 1.0:
            low_ctr.append((ad["name"], ctr, impressions))

    low_ctr.sort(key=lambda x: x[1])
    if low_ctr:
        detail = ", ".join(
            f"{name} (CTR {ctr:.2f}%, {imps} imps)"
            for name, ctr, imps in low_ctr[:5]
        )
        findings.append({
            "frente": "Criativo",
            "severity": "media",
            "titulo": f"{len(low_ctr)} anuncios com CTR abaixo de 1%",
            "descricao": (
                f"CTR baixo = criativo nao chama atencao, CPC sobe. "
                f"Anuncios: {detail}."
            ),
            "recomendacao": (
                "Teste hooks mais fortes nos primeiros 3 segundos do video. "
                "CTR bom pra arbitragem: > 3%. Abaixo de 1% e caso de trocar o criativo."
            ),
        })

    # 5. Ranking de CPC por anuncio (identifica campeao)
    ranked: list[tuple[str, float, float, str]] = []
    for ad in active_ads:
        ins = insights_by_ad.get(ad["id"])
        if not ins:
            continue
        spend = _safe_float(ins.get("spend"))
        cpc = _safe_float(ins.get("cpc"))
        if spend >= MIN_SPEND_FOR_CPC and cpc > 0:
            ranked.append((ad["name"], cpc, spend, ad.get("campaign_id", "")))

    ranked.sort(key=lambda x: x[1])
    if ranked:
        best = ranked[0]
        label = "Excelente" if best[1] < CPC_BOM else "Bom" if best[1] < CPC_MEDIOCRE else "Mediocre"
        detail = "\n".join(
            f"  {i+1}. {name} — CPC R${cpc:.2f} (gasto R${spend:.0f})"
            for i, (name, cpc, spend, _) in enumerate(ranked[:10])
        )
        findings.append({
            "frente": "Criativo",
            "severity": "baixa",
            "titulo": f"Ranking CPC — campeao: {best[0]} (R${best[1]:.2f}, {label})",
            "descricao": (
                f"Top anuncios por CPC:\n{detail}"
            ),
            "recomendacao": (
                f"Campeao atual: {best[0]} com CPC R${best[1]:.2f}. "
                "Duplique a campanha com esse criativo + 2 variacoes novas pra escalar."
                if best[1] < CPC_MEDIOCRE else
                "Nenhum anuncio com CPC bom (< R$0,15). Teste criativos novos."
            ),
        })

    return findings
