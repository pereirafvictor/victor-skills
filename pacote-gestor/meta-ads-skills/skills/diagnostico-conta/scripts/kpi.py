"""
kpi.py — KPI de cada campanha de acordo com o objetivo.

trafego → CPC | vendas → CPA | leads → CPL | engajamento → custo por engajamento.
Limites (bom/ruim) vêm do perfil.json do gestor.
"""
from __future__ import annotations

from typing import Any

OBJETIVO_PARA_TIPO = {
    "OUTCOME_TRAFFIC": "trafego", "LINK_CLICKS": "trafego",
    "OUTCOME_SALES": "vendas", "CONVERSIONS": "vendas", "PRODUCT_CATALOG_SALES": "vendas",
    "OUTCOME_LEADS": "leads", "LEAD_GENERATION": "leads",
    "OUTCOME_ENGAGEMENT": "engajamento", "POST_ENGAGEMENT": "engajamento",
    "VIDEO_VIEWS": "engajamento", "PAGE_LIKES": "engajamento", "MESSAGES": "engajamento",
}

ACOES = {
    "cpa": ["offsite_conversion.fb_pixel_purchase", "purchase", "omni_purchase"],
    "cpl": ["offsite_conversion.fb_pixel_lead", "lead", "onsite_conversion.lead_grouped"],
    "cpe": ["post_engagement"],
}

NOME_METRICA = {"cpc": "CPC", "cpa": "CPA", "cpl": "CPL", "cpe": "Custo/engajamento"}


def safe_float(val: Any) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def tipo_da_campanha(objective: str | None) -> str | None:
    return OBJETIVO_PARA_TIPO.get((objective or "").upper())


def resultados(ins: dict[str, Any], metrica: str) -> float:
    if metrica == "cpc":
        return safe_float(ins.get("clicks"))
    actions = {a.get("action_type"): safe_float(a.get("value")) for a in ins.get("actions") or []}
    for tipo in ACOES[metrica]:
        if actions.get(tipo):
            return actions[tipo]
    return 0.0


def custo(ins: dict[str, Any], metrica: str) -> float | None:
    """Custo por resultado. None quando não houve resultado."""
    if metrica == "cpc":
        cpc = safe_float(ins.get("cpc"))
        return cpc or None
    n = resultados(ins, metrica)
    return safe_float(ins.get("spend")) / n if n else None


def limites(perfil: dict, tipo: str) -> dict[str, Any]:
    return perfil["kpis"][tipo]


def fmt(valor: float, moeda: str) -> str:
    casas = 3 if valor < 0.1 else 2
    return f"{valor:.{casas}f} {moeda}"
