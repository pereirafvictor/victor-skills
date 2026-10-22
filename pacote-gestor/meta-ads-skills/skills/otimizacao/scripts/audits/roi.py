"""
roi.py — Auditoria de ROI cruzando Meta Ads com receita GAM.

Usa o CSV exportado do GAM (campanhas_YYYY-MM-DD.csv) para cruzar
investimento Meta com receita real.

Detecta:
- Campanhas com ROI abaixo de -70% (queimando dinheiro)
- Campanhas SEM FATURAMENTO (UTM ou flow quebrado)
- Ranking ROI por campanha (identifica qual escalar)
- Match rate baixo (leads que nao geram receita)
- CPL alto (custo por lead no Messenger)
"""
from __future__ import annotations

import csv
import glob
import os
from typing import Any


def _find_latest_csv(directory: str) -> str | None:
    pattern = os.path.join(directory, "campanhas_*.csv")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def _parse_csv(filepath: str) -> list[dict[str, str]]:
    rows = []
    with open(filepath, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            rows.append(row)
    return rows


def _safe_float(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def run(
    *,
    csv_path: str | None = None,
    csv_dir: str = "",
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not csv_path and not csv_dir:
        return findings  # gestor nao usa GAM — audit desligado

    if not csv_path:
        csv_path = _find_latest_csv(csv_dir)
    if not csv_path or not os.path.exists(csv_path):
        findings.append({
            "frente": "ROI",
            "severity": "media",
            "titulo": "CSV do GAM nao encontrado",
            "descricao": (
                f"Nenhum arquivo campanhas_*.csv encontrado em {csv_dir}. "
                "Sem ele nao da pra cruzar receita GAM com investimento Meta."
            ),
            "recomendacao": f"Exporte o CSV do GAM e salve em {csv_dir}.",
        })
        return findings

    rows = _parse_csv(csv_path)
    csv_name = os.path.basename(csv_path)

    facebook_rows = [
        r for r in rows
        if r.get("Source") == "facebook" and r.get("Status") == "ACTIVE"
    ]
    broad_rows = [
        r for r in rows
        if r.get("Source", "").endswith("-broad") and r.get("Source") != "facebook"
    ]

    if not facebook_rows:
        findings.append({
            "frente": "ROI",
            "severity": "media",
            "titulo": "Nenhuma campanha Facebook ativa no CSV",
            "descricao": f"O arquivo {csv_name} nao tem campanhas Facebook ativas.",
            "recomendacao": "Verifique se o CSV esta atualizado.",
        })
        return findings

    # 1. Campanhas SEM FATURAMENTO
    sem_fat = [
        r for r in facebook_rows
        if "SEM FATURMENTO" in (r.get("GAM") or "").upper()
        or "SEM FATURAMENTO" in (r.get("GAM") or "").upper()
    ]
    if sem_fat:
        nomes = [r.get("Campaign Name", "?") for r in sem_fat]
        findings.append({
            "frente": "ROI",
            "severity": "alta",
            "titulo": f"{len(sem_fat)} campanhas SEM FATURAMENTO no GAM",
            "descricao": (
                "Campanhas gastando no Meta sem registrar receita no GAM. "
                "Pode ser UTM errado, flow quebrado ou pagina sem ads. "
                f"Campanhas: {', '.join(nomes[:5])}"
                + (f" (+{len(nomes) - 5})" if len(nomes) > 5 else "")
                + "."
            ),
            "recomendacao": (
                "Verifique: 1) UTM da campanha bate com o GAM, "
                "2) Flow do chatbot esta enviando o link correto, "
                "3) Pagina do blog tem ads do GAM configurados."
            ),
        })

    # 2. Campanhas com ROI abaixo de -70%
    com_fat = [r for r in facebook_rows if r not in sem_fat]
    roi_ruim: list[tuple[str, float, float, float, float]] = []
    for r in com_fat:
        invest = _safe_float(r.get("Investimento (US$)"))
        receita = _safe_float(r.get("Receita (US$)"))
        roi_bruto = _safe_float(r.get("ROI Bruto"))
        match_rate = _safe_float(r.get("Match Rate"))
        if invest >= 1.0 and roi_bruto < -0.70:
            nome = r.get("Campaign Name", "?")
            roi_ruim.append((nome, roi_bruto, invest, receita, match_rate))

    roi_ruim.sort(key=lambda x: x[1])
    if roi_ruim:
        detail = ", ".join(
            f"{nome[:40]} (ROI {roi*100:.0f}%, gastou ${inv:.2f}, recebeu ${rec:.2f})"
            for nome, roi, inv, rec, _ in roi_ruim[:5]
        )
        findings.append({
            "frente": "ROI",
            "severity": "alta",
            "titulo": f"{len(roi_ruim)} campanhas com ROI abaixo de -70%",
            "descricao": (
                f"Campanhas queimando dinheiro sem retorno suficiente: {detail}"
                + (f" (+{len(roi_ruim) - 5})" if len(roi_ruim) > 5 else "")
                + "."
            ),
            "recomendacao": (
                "Avalie cada campanha: se match rate < 10%, o problema esta no flow/chatbot. "
                "Se match rate > 20% mas ROI ruim, o RPM da pagina esta baixo. "
                "Considere pausar campanhas com ROI < -90%."
            ),
        })

    # 3. Match rate baixo
    low_match: list[tuple[str, float, float, int]] = []
    for r in com_fat:
        invest = _safe_float(r.get("Investimento (US$)"))
        match_rate = _safe_float(r.get("Match Rate"))
        leads = int(_safe_float(r.get("Leads")))
        if invest >= 1.0 and match_rate < 0.10 and leads > 0:
            nome = r.get("Campaign Name", "?")
            low_match.append((nome, match_rate, invest, leads))

    low_match.sort(key=lambda x: x[1])
    if low_match:
        detail = ", ".join(
            f"{nome[:35]} (match {mr*100:.0f}%, {leads} leads)"
            for nome, mr, _, leads in low_match[:5]
        )
        findings.append({
            "frente": "ROI",
            "severity": "media",
            "titulo": f"{len(low_match)} campanhas com match rate abaixo de 10%",
            "descricao": (
                "Leads entram no Messenger mas nao clicam no link ou nao registram no GAM. "
                f"Campanhas: {detail}"
                + (f" (+{len(low_match) - 5})" if len(low_match) > 5 else "")
                + "."
            ),
            "recomendacao": (
                "Revise o flow do chatbot: o link esta visivel? O CTA esta claro? "
                "Teste tambem se a pagina de destino carrega corretamente."
            ),
        })

    # 4. CPL alto (> $5)
    high_cpl: list[tuple[str, float, int, float]] = []
    for r in facebook_rows:
        cpl = _safe_float(r.get("CPL"))
        leads = int(_safe_float(r.get("Leads")))
        invest = _safe_float(r.get("Investimento (US$)"))
        if leads >= 3 and cpl > 5.0:
            nome = r.get("Campaign Name", "?")
            high_cpl.append((nome, cpl, leads, invest))

    high_cpl.sort(key=lambda x: x[1], reverse=True)
    if high_cpl:
        detail = ", ".join(
            f"{nome[:35]} (CPL ${cpl:.2f}, {leads} leads)"
            for nome, cpl, leads, _ in high_cpl[:5]
        )
        findings.append({
            "frente": "ROI",
            "severity": "media",
            "titulo": f"{len(high_cpl)} campanhas com CPL acima de $5",
            "descricao": (
                "Custo por lead no Messenger muito alto. Cada conversa custa mais "
                f"que o retorno possivel no GAM. Campanhas: {detail}"
                + (f" (+{len(high_cpl) - 5})" if len(high_cpl) > 5 else "")
                + "."
            ),
            "recomendacao": (
                "CPL alto = criativo nao engaja ou publico errado. "
                "Teste criativos novos e considere estreitar publico pra 45-65."
            ),
        })

    # 5. Ranking ROI por campanha
    all_camps: list[tuple[str, float, float, float, float, int, str]] = []
    for r in facebook_rows:
        invest = _safe_float(r.get("Investimento (US$)"))
        if invest < 1.0:
            continue
        receita = _safe_float(r.get("Receita (US$)"))
        roi_bruto = _safe_float(r.get("ROI Bruto"))
        match_rate = _safe_float(r.get("Match Rate"))
        leads = int(_safe_float(r.get("Leads")))
        cpl = _safe_float(r.get("CPL"))
        nome = r.get("Campaign Name", "?")
        status = r.get("Status", "?")
        all_camps.append((nome, roi_bruto, invest, receita, match_rate, leads, status))

    all_camps.sort(key=lambda x: x[1], reverse=True)
    if all_camps:
        detail_lines = []
        for i, (nome, roi, inv, rec, mr, leads, status) in enumerate(all_camps[:10], 1):
            roi_pct = f"{roi*100:.0f}%"
            paused = " [PAUSED]" if status == "PAUSED" else ""
            detail_lines.append(
                f"  {i}. {nome[:45]}{paused}\n"
                f"     ROI: {roi_pct} | Gastou: ${inv:.2f} | Receita: ${rec:.2f} | "
                f"Match: {mr*100:.0f}% | Leads: {leads}"
            )
        detail = "\n".join(detail_lines)
        best = all_camps[0]
        findings.append({
            "frente": "ROI",
            "severity": "baixa",
            "titulo": f"Ranking ROI — melhor: {best[0][:30]} (ROI {best[1]*100:.0f}%)",
            "descricao": f"Campanhas ordenadas por ROI:\n{detail}",
            "recomendacao": (
                f"Melhor campanha: {best[0][:30]} com ROI {best[1]*100:.0f}%. "
                "Escale as campanhas com melhor ROI e pause as piores."
                if best[1] > -0.50 else
                "Nenhuma campanha com ROI aceitavel (> -50%). "
                "Foco em melhorar flow e match rate antes de escalar."
            ),
        })

    # 6. Receita Broad (bonus sem custo)
    total_broad = sum(_safe_float(r.get("Receita (US$)")) for r in broad_rows)
    if total_broad > 0:
        top_broad = sorted(
            broad_rows,
            key=lambda r: _safe_float(r.get("Receita (US$)")),
            reverse=True,
        )
        detail = ", ".join(
            f"{r.get('Source', '?')} (${_safe_float(r.get('Receita (US$)')):.2f})"
            for r in top_broad[:5]
        )
        findings.append({
            "frente": "ROI",
            "severity": "baixa",
            "titulo": f"Receita Broad total: ${total_broad:.2f} (lucro puro)",
            "descricao": (
                f"Trafego organico gerando receita sem custo de ads. "
                f"Top sources: {detail}."
            ),
            "recomendacao": (
                "Broad e lucro puro. Paginas com mais broad sao as que tem melhor SEO/conteudo. "
                "Priorize criativos e campanhas pagas nessas paginas."
            ),
        })

    return findings
