"""
render.py — Renderiza findings no terminal (sem Obsidian).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

SEVERITY_ORDER = {"alta": 0, "media": 1, "baixa": 2}

SEVERITY_HEADERS = {
    "alta": "CRITICO (alta prioridade)",
    "media": "ATENCAO (media prioridade)",
    "baixa": "MELHORIA (baixa prioridade)",
}

SEVERITY_EMOJI = {
    "alta": "[!!]",
    "media": "[!]",
    "baixa": "[i]",
}


def _normalize_severity(sev: str) -> str:
    sev = (sev or "").strip().lower()
    if sev in ("media", "média"):
        return "media"
    if sev == "alta":
        return "alta"
    return "baixa"


def prioritize(findings: list[dict[str, Any]], *, max_total: int = 15) -> list[dict[str, Any]]:
    normalized = []
    for f in findings:
        f2 = dict(f)
        f2["severity"] = _normalize_severity(f2.get("severity", "baixa"))
        normalized.append(f2)
    normalized.sort(key=lambda f: SEVERITY_ORDER.get(f["severity"], 99))
    return normalized[:max_total]


def summary(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"alta": 0, "media": 0, "baixa": 0}
    for f in findings:
        counts[_normalize_severity(f.get("severity", "baixa"))] += 1
    return counts


def render_terminal(
    *,
    findings: list[dict[str, Any]],
    skipped_audits: list[str],
    errored_audits: list[tuple[str, str]],
    account_info: dict[str, Any] | None,
    generated_at: datetime,
) -> str:
    findings = prioritize(findings)
    counts = summary(findings)
    total = len(findings)

    lines: list[str] = []
    date_iso = generated_at.strftime("%Y-%m-%d %H:%M")

    lines.append("=" * 60)
    lines.append("  DIAGNOSTICO DE CONTA — ARBITRAGEM")
    lines.append("=" * 60)
    lines.append("")

    if account_info:
        nome = account_info.get("name") or "?"
        moeda = account_info.get("currency") or ""
        tz = account_info.get("timezone_name") or ""
        spent = account_info.get("amount_spent")
        spent_str = f" | Gasto total: {float(spent)/100:.2f} {moeda}" if spent else ""
        lines.append(f"  Conta: {nome} | {moeda} | {tz}{spent_str}")

    lines.append(f"  Data: {date_iso}")
    lines.append(f"  Findings: {total} ({counts['alta']} criticos, "
                 f"{counts['media']} medios, {counts['baixa']} menores)")
    lines.append("")

    if skipped_audits:
        lines.append(f"  Audits pulados: {', '.join(skipped_audits)}")
        lines.append("")

    if errored_audits:
        for name, err in errored_audits:
            lines.append(f"  [ERRO] Audit `{name}`: {err}")
        lines.append("")

    if total == 0:
        lines.append("  Nenhum problema detectado nos audits automatizados.")
        lines.append("  Isso nao significa conta perfeita — revisao manual ainda agrega.")
        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    by_sev: dict[str, list[dict[str, Any]]] = {"alta": [], "media": [], "baixa": []}
    for f in findings:
        by_sev[_normalize_severity(f["severity"])].append(f)

    for sev in ("alta", "media", "baixa"):
        items = by_sev[sev]
        if not items:
            continue
        lines.append("-" * 60)
        lines.append(f"  {SEVERITY_EMOJI[sev]} {SEVERITY_HEADERS[sev]}")
        lines.append("-" * 60)
        lines.append("")

        for f in items:
            lines.append(f"  > {f.get('titulo', '(sem titulo)')}")
            lines.append(f"    Frente: {f.get('frente', '-')}")
            descricao = (f.get("descricao") or "").strip()
            recomendacao = (f.get("recomendacao") or "").strip()
            lines.append(f"    {descricao}")
            lines.append(f"    Recomendacao: {recomendacao}")
            lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
