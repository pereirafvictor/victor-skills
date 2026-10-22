"""
publico.py — Auditoria de publico.

Detecta:
- Overlap entre conjuntos da mesma campanha
- Idade ampla demais sem segmentacao
- Lookalikes com seed velha (> 90 dias)
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _interest_set(adset: dict[str, Any]) -> set[str]:
    t = adset.get("targeting") or {}
    ids: set[str] = set()
    spec = t.get("flexible_spec") or [t.get("targeting_spec")] or []
    if isinstance(spec, list):
        for block in spec:
            if not block:
                continue
            for it in (block.get("interests") or []):
                key = str(it.get("id") or it.get("name") or "")
                if key:
                    ids.add(key)
            for it in (block.get("behaviors") or []):
                key = str(it.get("id") or it.get("name") or "")
                if key:
                    ids.add(f"b:{key}")
    for ca in (t.get("custom_audiences") or []):
        ids.add(f"ca:{ca.get('id')}")
    return ids


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def run(
    *,
    adsets: list[dict[str, Any]],
    custom_audiences: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    active_adsets = [a for a in adsets if a.get("effective_status") == "ACTIVE"]

    # 1. Overlap entre conjuntos da mesma campanha
    by_campaign: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in active_adsets:
        by_campaign[a.get("campaign_id", "")].append(a)

    overlap_pairs: list[tuple[str, str, float, int]] = []
    for camp_id, group in by_campaign.items():
        sigs = [(a, _interest_set(a)) for a in group]
        for i in range(len(sigs)):
            for j in range(i + 1, len(sigs)):
                a1, s1 = sigs[i]
                a2, s2 = sigs[j]
                if not s1 or not s2:
                    continue
                j_score = _jaccard(s1, s2)
                if j_score > 0.30:
                    overlap_pairs.append((a1["name"], a2["name"], j_score, len(s1 & s2)))

    overlap_pairs.sort(key=lambda x: x[2], reverse=True)
    for n1, n2, score, shared in overlap_pairs[:5]:
        findings.append({
            "frente": "Publico",
            "severity": "alta",
            "titulo": f"Overlap {score * 100:.0f}% entre `{n1}` e `{n2}`",
            "descricao": (
                f"Os dois conjuntos compartilham {shared} interesses — overlap "
                f"estimado em {score * 100:.0f}% (Jaccard). Estao competindo pelo "
                "mesmo publico, inflando o custo."
            ),
            "recomendacao": (
                "Consolide num so conjunto (mantenha o de melhor resultado). "
                "Se quer testar variacoes, use exclusoes mutuas."
            ),
        })

    # 2. Idade ampla sem segmentacao
    wide_age: list[str] = []
    for adset in active_adsets:
        t = adset.get("targeting") or {}
        age_min = int(t.get("age_min", 0) or 0)
        age_max = int(t.get("age_max", 0) or 0)
        wide = (age_max - age_min) >= 40 or (age_min <= 18 and age_max >= 60)
        interests = _interest_set(adset)
        if wide and not interests:
            wide_age.append(f"{adset['name']} ({age_min}-{age_max})")

    if wide_age:
        findings.append({
            "frente": "Publico",
            "severity": "baixa",
            "titulo": f"{len(wide_age)} conjuntos com idade muito ampla e sem segmentacao",
            "descricao": (
                "Faixas de idade abertas (18-65) sem interesse/comportamento "
                "deixam o algoritmo decidir tudo. Pode funcionar com historico, "
                f"mas dilui entrega com budget baixo. Conjuntos: {', '.join(wide_age[:5])}"
                + (f" (+{len(wide_age) - 5})" if len(wide_age) > 5 else "")
                + "."
            ),
            "recomendacao": (
                "Se a conta tem pouco historico, estreite a faixa de idade pro "
                "publico que mais converte ou adicione interesses relevantes."
            ),
        })

    # 3. Lookalikes com seed velha
    stale_lookalikes: list[tuple[str, int]] = []
    for ca in custom_audiences:
        if ca.get("subtype") != "LOOKALIKE":
            continue
        updated = _parse_dt(ca.get("time_updated") or ca.get("time_created"))
        if not updated:
            continue
        days = (now - updated).days
        if days > 90:
            stale_lookalikes.append((ca.get("name", "?"), days))

    stale_lookalikes.sort(key=lambda x: x[1], reverse=True)
    for name, days in stale_lookalikes[:5]:
        findings.append({
            "frente": "Publico",
            "severity": "media",
            "titulo": f"Lookalike `{name}` sem refresh ha {days} dias",
            "descricao": (
                f"Lookalikes degradam com o tempo. {days} dias sem atualizar "
                "significa que a Meta expande a partir de uma base desatualizada."
            ),
            "recomendacao": (
                "Recrie a seed com conversoes dos ultimos 60-90 dias e gere "
                "lookalike novo."
            ),
        })

    return findings
