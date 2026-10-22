"""
estrutura.py — Auditoria de estrutura para arbitragem.

Modelo esperado: 1 campanha x 1 conjunto x 3 anuncios (escala).

Detecta:
- Campanhas com mais de 1 conjunto (fora do modelo escala)
- Campanhas com numero errado de anuncios (esperado: 3)
- Campanhas duplicadas (mesmo objetivo + mesmo targeting)
- Conjuntos pausados ha mais de 14 dias (lixo)
- Campanhas sem objetivo TRAFFIC (unico objetivo valido pra arbitragem)
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


def run(
    *,
    campaigns: list[dict[str, Any]],
    adsets: list[dict[str, Any]],
    ads: list[dict[str, Any]],
    insights_by_campaign: dict[str, dict[str, Any]],
    insights_by_adset: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    adsets_by_campaign: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in adsets:
        adsets_by_campaign[a.get("campaign_id", "")].append(a)

    ads_by_adset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ads_by_campaign: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ad in ads:
        ads_by_adset[ad.get("adset_id", "")].append(ad)
        ads_by_campaign[ad.get("campaign_id", "")].append(ad)

    active_campaigns = [c for c in campaigns if c.get("effective_status") == "ACTIVE"]
    camp_map = {c["id"]: c for c in campaigns if "id" in c}

    # 1. Campanhas com mais de 1 conjunto (fora do modelo escala)
    multi_adset: list[str] = []
    for camp in active_campaigns:
        cid = camp["id"]
        n_adsets = len(adsets_by_campaign.get(cid, []))
        if n_adsets > 1:
            multi_adset.append(f"{camp['name']} ({n_adsets} conjuntos)")

    if multi_adset:
        findings.append({
            "frente": "Estrutura",
            "severity": "alta",
            "titulo": f"{len(multi_adset)} campanhas com mais de 1 conjunto",
            "descricao": (
                "O modelo escala usa 1 campanha x 1 conjunto x 3 anuncios. "
                f"Campanhas com multiplos conjuntos dividem budget e competem entre si: "
                f"{', '.join(multi_adset[:5])}"
                + (f" (+{len(multi_adset) - 5})" if len(multi_adset) > 5 else "")
                + "."
            ),
            "recomendacao": (
                "Consolide em 1 conjunto por campanha. Se quer testar publicos diferentes, "
                "crie campanhas separadas (cada uma com 1 conjunto)."
            ),
        })

    # 2. Campanhas com numero errado de anuncios
    wrong_ad_count: list[str] = []
    for camp in active_campaigns:
        cid = camp["id"]
        n_ads = len([
            ad for ad in ads_by_campaign.get(cid, [])
            if ad.get("effective_status") == "ACTIVE"
        ])
        if n_ads != 3 and n_ads > 0:
            wrong_ad_count.append(f"{camp['name']} ({n_ads} ads)")

    if wrong_ad_count:
        sev = "media"
        findings.append({
            "frente": "Estrutura",
            "severity": sev,
            "titulo": f"{len(wrong_ad_count)} campanhas sem 3 anuncios ativos",
            "descricao": (
                "O modelo escala espera 3 anuncios por conjunto pra testar criativos e "
                f"encontrar o campeao. Campanhas fora do padrao: "
                f"{', '.join(wrong_ad_count[:5])}"
                + (f" (+{len(wrong_ad_count) - 5})" if len(wrong_ad_count) > 5 else "")
                + "."
            ),
            "recomendacao": (
                "Ajuste pra 3 anuncios por conjunto. Menos = teste incompleto, "
                "mais = budget diluido entre criativos demais."
            ),
        })

    # 3. Objetivo errado (nao TRAFFIC)
    wrong_objective: list[str] = []
    for camp in active_campaigns:
        obj = (camp.get("objective") or "").upper()
        if "TRAFFIC" not in obj and "LINK_CLICKS" not in obj and "OUTCOME_TRAFFIC" not in obj:
            wrong_objective.append(f"{camp['name']} (obj: {camp.get('objective', '?')})")

    if wrong_objective:
        findings.append({
            "frente": "Estrutura",
            "severity": "alta",
            "titulo": f"{len(wrong_objective)} campanhas sem objetivo TRAFFIC",
            "descricao": (
                "Arbitragem precisa de cliques baratos — objetivo TRAFFIC. "
                f"Campanhas com outro objetivo: {', '.join(wrong_objective[:5])}"
                + (f" (+{len(wrong_objective) - 5})" if len(wrong_objective) > 5 else "")
                + "."
            ),
            "recomendacao": (
                "Recrie essas campanhas com objetivo OUTCOME_TRAFFIC. "
                "Campanhas de ENGAGEMENT ou CONVERSIONS custam CPC mais caro."
            ),
        })

    # 4. Conjuntos pausados ha mais de 14 dias
    stale_paused: list[str] = []
    for adset in adsets:
        if adset.get("effective_status") != "PAUSED":
            continue
        updated = _parse_dt(adset.get("updated_time"))
        if updated and (now - updated).days > 14:
            days = (now - updated).days
            stale_paused.append(f"{adset['name']} ({days}d paused)")

    if stale_paused:
        findings.append({
            "frente": "Estrutura",
            "severity": "baixa",
            "titulo": f"{len(stale_paused)} conjuntos pausados ha mais de 14 dias",
            "descricao": (
                f"Conjuntos que ficam parados so poluem a conta. "
                f"Exemplos: {', '.join(stale_paused[:5])}"
                + (f" (+{len(stale_paused) - 5})" if len(stale_paused) > 5 else "")
                + "."
            ),
            "recomendacao": (
                "Archive ou delete esses conjuntos pra manter a conta limpa. "
                "Se quiser reativar algum, crie campanha nova — conjunto velho perde aprendizado."
            ),
        })

    # 5. Campanhas duplicadas (mesmo objetivo + targeting similar)
    active_sigs: list[tuple[str, str, str]] = []
    for camp in active_campaigns:
        cid = camp["id"]
        camp_adsets = adsets_by_campaign.get(cid, [])
        obj = camp.get("objective", "")
        for adset in camp_adsets:
            t = adset.get("targeting") or {}
            countries_raw = t.get("geo_locations", {}).get("countries") or []
            country_keys = []
            for c in countries_raw:
                if isinstance(c, dict):
                    country_keys.append(c.get("key", ""))
                else:
                    country_keys.append(str(c))
            geo = str(sorted(country_keys))
            sig = f"{obj}|{geo}"
            active_sigs.append((camp["name"], cid, sig))

    seen_sigs: dict[str, list[str]] = defaultdict(list)
    for name, cid, sig in active_sigs:
        seen_sigs[sig].append(name)

    for sig, names in seen_sigs.items():
        if len(names) > 1:
            findings.append({
                "frente": "Estrutura",
                "severity": "media",
                "titulo": f"{len(names)} campanhas potencialmente duplicadas",
                "descricao": (
                    f"Campanhas com mesmo objetivo + pais competem pelo mesmo publico: "
                    f"{', '.join(names[:4])}"
                    + (f" (+{len(names) - 4})" if len(names) > 4 else "")
                    + ". Na arbitragem isso infla o CPC."
                ),
                "recomendacao": (
                    "Mantenha so a de melhor CPC e pause as demais, ou use "
                    "criativos/paginas diferentes pra diferenciar."
                ),
            })

    return findings
