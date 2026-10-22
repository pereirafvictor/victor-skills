"""
criativo.py — Auditoria de criativos.

KPI de cada anúncio depende do objetivo da campanha (ver kpi.py).

Detecta:
- Custo por resultado acima do limite "ruim" do perfil
- Gasto sem nenhum resultado (vendas/leads)
- Fadiga criativa (frequencia > 3x + idade > 14 dias)
- Pouca variacao criativa (menos anuncios que o padrao do perfil)
- CTR baixo (< 1%) apos 1000+ impressoes
- Ranking por custo/resultado em cada objetivo (identifica campeao)
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import kpi

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


def run(
    *,
    ads: list[dict[str, Any]],
    adsets: list[dict[str, Any]],
    campaigns: list[dict[str, Any]],
    insights_by_ad: dict[str, dict[str, Any]],
    perfil: dict[str, Any],
    moeda: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    adset_map = {a["id"]: a for a in adsets if "id" in a}
    camp_tipo = {c["id"]: kpi.tipo_da_campanha(c.get("objective")) for c in campaigns if "id" in c}
    active_ads = [a for a in ads if a.get("effective_status") == "ACTIVE"]

    # Agrupa anuncios ativos com insight por tipo de objetivo
    por_tipo: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    for ad in active_ads:
        ins = insights_by_ad.get(ad["id"])
        tipo = camp_tipo.get(ad.get("campaign_id", ""))
        if ins and tipo:
            por_tipo[tipo].append((ad, ins))

    for tipo, itens in por_tipo.items():
        lim = kpi.limites(perfil, tipo)
        metrica = lim["metrica"]
        nome_m = kpi.NOME_METRICA[metrica]
        # gasto minimo pra julgar: 3x o limite "ruim" (ou 10 na moeda, o que for maior)
        min_spend = max(10.0, lim["ruim"] * 3)

        # 1. Custo por resultado alto
        caros: list[tuple[str, float, float]] = []
        sem_resultado: list[tuple[str, float]] = []
        ranked: list[tuple[str, float, float]] = []
        for ad, ins in itens:
            spend = kpi.safe_float(ins.get("spend"))
            if spend < min_spend:
                continue
            c = kpi.custo(ins, metrica)
            if c is None:
                if metrica != "cpc":
                    sem_resultado.append((ad["name"], spend))
                continue
            ranked.append((ad["name"], c, spend))
            if c > lim["ruim"]:
                caros.append((ad["name"], c, spend))

        caros.sort(key=lambda x: x[1], reverse=True)
        if caros:
            detail = ", ".join(
                f"{n} ({nome_m} {kpi.fmt(c, moeda)}, gasto {s:.0f})" for n, c, s in caros[:5]
            )
            findings.append({
                "frente": "Criativo",
                "severity": "alta",
                "titulo": f"{len(caros)} anuncios de {tipo} com {nome_m} acima de {kpi.fmt(lim['ruim'], moeda)}",
                "descricao": f"Anuncios acima do limite do seu perfil: {detail}.",
                "recomendacao": (
                    "Pause esses anuncios e substitua por criativos novos. "
                    "Se todos os anuncios do conjunto estao ruins, revise publico/oferta antes de trocar criativo."
                ),
            })

        sem_resultado.sort(key=lambda x: x[1], reverse=True)
        if sem_resultado:
            detail = ", ".join(f"{n} (gasto {s:.0f})" for n, s in sem_resultado[:5])
            findings.append({
                "frente": "Criativo",
                "severity": "alta",
                "titulo": f"{len(sem_resultado)} anuncios de {tipo} gastando sem nenhum resultado",
                "descricao": f"Gastaram mais de {min_spend:.0f} {moeda} sem gerar {nome_m.split('/')[0]}: {detail}.",
                "recomendacao": (
                    "Confira se o pixel/evento esta disparando (Gerenciador de Eventos). "
                    "Se estiver, pause o anuncio."
                ),
            })

        # 2. Ranking (campeao)
        ranked.sort(key=lambda x: x[1])
        if ranked:
            best = ranked[0]
            label = "bom" if best[1] <= lim["bom"] else "ruim" if best[1] > lim["ruim"] else "mediano"
            detail = "\n".join(
                f"  {i + 1}. {n} — {nome_m} {kpi.fmt(c, moeda)} (gasto {s:.0f})"
                for i, (n, c, s) in enumerate(ranked[:10])
            )
            findings.append({
                "frente": "Criativo",
                "severity": "baixa",
                "titulo": f"Ranking {nome_m} ({tipo}) — campeao: {best[0]} ({kpi.fmt(best[1], moeda)}, {label})",
                "descricao": f"Top anuncios por {nome_m}:\n{detail}",
                "recomendacao": (
                    f"Campeao: {best[0]}. Duplique com esse criativo + variacoes novas pra escalar."
                    if best[1] <= lim["ruim"] else
                    f"Nenhum anuncio dentro do limite ({kpi.fmt(lim['ruim'], moeda)}). Teste criativos novos."
                ),
            })

    # 3. Fadiga criativa (frequencia alta + idade > 14 dias)
    fatigued: list[tuple[str, float, int]] = []
    for ad in active_ads:
        ins = insights_by_ad.get(ad["id"])
        created = _parse_dt(ad.get("created_time"))
        if not ins or not created:
            continue
        freq = kpi.safe_float(ins.get("frequency"))
        age_days = (now - created).days
        if freq > FREQ_LIMIT and age_days > AGE_LIMIT_DAYS:
            fatigued.append((ad["name"], freq, age_days))

    fatigued.sort(key=lambda x: x[1], reverse=True)
    if fatigued:
        detail = ", ".join(f"{n} (freq {f:.1f}x, {d}d)" for n, f, d in fatigued[:5])
        findings.append({
            "frente": "Criativo",
            "severity": "alta",
            "titulo": f"{len(fatigued)} anuncios com fadiga criativa",
            "descricao": f"Frequencia alta + anuncio velho = publico saturado, custo sobe. Anuncios: {detail}.",
            "recomendacao": "Troque os criativos fatigados por novos e rotacione a cada 2-3 semanas.",
        })

    # 4. Pouca variacao criativa
    esperado = perfil["estrutura"]["anuncios_por_conjunto"]
    ads_by_adset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ad in active_ads:
        ads_by_adset[ad.get("adset_id", "")].append(ad)

    low_variation: list[str] = []
    for adset_id, adset_ads in ads_by_adset.items():
        if len(adset_ads) < esperado:
            adset = adset_map.get(adset_id)
            name = adset["name"] if adset else adset_id
            low_variation.append(f"{name} ({len(adset_ads)} ads)")

    if low_variation:
        findings.append({
            "frente": "Criativo",
            "severity": "media",
            "titulo": f"{len(low_variation)} conjuntos com menos de {esperado} anuncios",
            "descricao": (
                f"Seu padrao e {esperado} anuncios por conjunto pra achar o campeao. "
                f"Conjuntos incompletos: {', '.join(low_variation[:5])}"
                + (f" (+{len(low_variation) - 5})" if len(low_variation) > 5 else "")
                + "."
            ),
            "recomendacao": "Complete com criativos novos — sem variacao nao da pra saber qual performa melhor.",
        })

    # 5. CTR baixo (< 1%) apos impressoes suficientes
    low_ctr: list[tuple[str, float, int]] = []
    for ad in active_ads:
        ins = insights_by_ad.get(ad["id"])
        if not ins:
            continue
        impressions = int(kpi.safe_float(ins.get("impressions")))
        ctr = kpi.safe_float(ins.get("ctr"))
        if impressions >= MIN_IMPRESSIONS_FOR_CTR and ctr < 1.0:
            low_ctr.append((ad["name"], ctr, impressions))

    low_ctr.sort(key=lambda x: x[1])
    if low_ctr:
        detail = ", ".join(f"{n} (CTR {c:.2f}%, {i} imps)" for n, c, i in low_ctr[:5])
        findings.append({
            "frente": "Criativo",
            "severity": "media",
            "titulo": f"{len(low_ctr)} anuncios com CTR abaixo de 1%",
            "descricao": f"CTR baixo = criativo nao chama atencao. Anuncios: {detail}.",
            "recomendacao": "Teste hooks mais fortes nos primeiros 3 segundos. Abaixo de 1% e caso de trocar o criativo.",
        })

    return findings
