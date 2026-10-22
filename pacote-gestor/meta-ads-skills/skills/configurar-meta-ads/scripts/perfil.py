"""
perfil.py — carrega a configuração do gestor (token + perfil.json).

Tudo que é pessoal (token, conta, pixel, páginas, domínios, KPIs) fica em
~/.meta-ads/ — fora das skills, então atualizar as skills não apaga nada.
Pode trocar a pasta com a variável de ambiente META_ADS_HOME.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Terminal do Windows usa cp1252 por padrão e quebra com ✓/✗/acentos
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

HOME = Path(os.getenv("META_ADS_HOME") or Path.home() / ".meta-ads")
ENV_PATH = HOME / ".env"
PERFIL_PATH = HOME / "perfil.json"

DEFAULTS = {
    "api_version": "v23.0",
    "moeda": "BRL",
    "objetivo_padrao": "trafego",
    "pixel_id": "",
    "evento_conversao": "PURCHASE",
    "paginas": [],
    "destinos": [],
    "utm": "",
    "publico": {
        "idade_min": 18,
        "idade_max": 65,
        "advantage_plus": False,
        "posicionamentos": {
            "publisher_platforms": ["facebook", "instagram"],
            "facebook_positions": ["feed", "story"],
            "instagram_positions": ["stream", "story"],
        },
    },
    "estrutura": {"conjuntos": 1, "anuncios_por_conjunto": 3},
    "cta": "LEARN_MORE",
    "textos": {},
    "dsa_beneficiario": "",
    "orcamento_max_diario": 0,
    "objetivos_permitidos": [],
    "kpis": {
        "trafego":     {"metrica": "cpc", "bom": 0.15, "ruim": 0.40},
        "vendas":      {"metrica": "cpa", "bom": 30.0, "ruim": 80.0},
        "leads":       {"metrica": "cpl", "bom": 5.0,  "ruim": 15.0},
        "engajamento": {"metrica": "cpe", "bom": 0.02, "ruim": 0.08},
    },
    "gam_csv_dir": "",
}


def _merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def carregar(*, exigir_perfil: bool = True) -> dict:
    """Carrega .env + perfil.json. Sai com código 3 se não estiver configurado."""
    load_dotenv(ENV_PATH)
    if not PERFIL_PATH.exists():
        if exigir_perfil:
            print(f"✗ Perfil não encontrado em {PERFIL_PATH}")
            print("  Rode a skill configurar-meta-ads primeiro (\"configura meu meta ads\").")
            sys.exit(3)
        perfil = dict(DEFAULTS)
    else:
        with open(PERFIL_PATH, encoding="utf-8") as f:
            perfil = _merge(DEFAULTS, json.load(f))

    perfil["_token"] = (os.getenv("META_ACCESS_TOKEN") or "").strip()
    conta = (perfil.get("ad_account_id") or os.getenv("META_AD_ACCOUNT_ID") or "").strip()
    if conta and not conta.startswith("act_"):
        conta = f"act_{conta}"
    perfil["ad_account_id"] = conta
    return perfil


def achar(lista: list[dict], chave: str | None) -> dict | None:
    """Acha página/destino por apelido, id ou nome (sem diferenciar maiúsculas)."""
    if not lista:
        return None
    if not chave:
        return lista[0] if len(lista) == 1 else None
    c = chave.strip().lower()
    for item in lista:
        if c in {str(item.get(k, "")).lower() for k in ("apelido", "id", "nome", "url")}:
            return item
    return None
