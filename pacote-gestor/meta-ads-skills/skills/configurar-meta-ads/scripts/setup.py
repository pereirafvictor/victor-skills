"""
setup.py — configuração inicial das skills de Meta Ads.

Uso:
    python setup.py checar                 # valida token e permissões
    python setup.py descobrir              # lista contas de anúncio e páginas
    python setup.py descobrir --conta act_X  # + pixels dessa conta
    python setup.py validar                # confere o perfil.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perfil as P

PERMISSOES_NECESSARIAS = {"ads_management", "ads_read", "pages_show_list", "pages_read_engagement"}
OBJETIVOS = {"trafego", "vendas", "leads", "engajamento"}


def _get(cfg: dict, path: str, **params) -> dict:
    params["access_token"] = cfg["_token"]
    r = requests.get(f"https://graph.facebook.com/{cfg['api_version']}/{path}", params=params, timeout=30)
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", r.text))
    return data


def _todos(cfg: dict, path: str, **params) -> list[dict]:
    out, data = [], _get(cfg, path, limit=100, **params)
    while True:
        out.extend(data.get("data", []))
        nxt = (data.get("paging") or {}).get("next")
        if not nxt:
            return out
        data = requests.get(nxt, timeout=30).json()


def checar(cfg: dict) -> int:
    if not cfg["_token"]:
        print(f"✗ META_ACCESS_TOKEN vazio em {P.ENV_PATH}")
        return 2
    try:
        me = _get(cfg, "me", fields="id,name")
        perms = _get(cfg, "me/permissions")["data"]
    except RuntimeError as e:
        print(f"✗ Token inválido: {e}")
        return 2
    concedidas = {p["permission"] for p in perms if p.get("status") == "granted"}
    print(f"✓ Token OK — usuário: {me.get('name', me['id'])}")
    faltando = PERMISSOES_NECESSARIAS - concedidas
    if faltando:
        print(f"✗ Permissões faltando: {', '.join(sorted(faltando))}")
        print("  Gere o token de novo marcando essas permissões.")
        return 2
    print("✓ Permissões OK")
    return 0


def descobrir(cfg: dict, conta: str | None) -> int:
    saida: dict = {}
    contas = _todos(cfg, "me/adaccounts", fields="account_id,name,currency,account_status")
    saida["contas"] = [
        {"id": f"act_{c['account_id']}", "nome": c.get("name"), "moeda": c.get("currency"),
         "ativa": c.get("account_status") == 1}
        for c in contas
    ]
    paginas = _todos(cfg, "me/accounts", fields="id,name")
    saida["paginas"] = [{"id": p["id"], "nome": p["name"]} for p in paginas]
    if conta:
        if not conta.startswith("act_"):
            conta = f"act_{conta}"
        pixels = _todos(cfg, f"{conta}/adspixels", fields="id,name,last_fired_time")
        saida["pixels"] = [
            {"id": p["id"], "nome": p.get("name"), "ultimo_disparo": p.get("last_fired_time")}
            for p in pixels
        ]
    print(json.dumps(saida, ensure_ascii=False, indent=2))
    return 0


def validar(cfg: dict) -> int:
    erros, avisos = [], []
    if not P.PERFIL_PATH.exists():
        print(f"✗ {P.PERFIL_PATH} não existe")
        return 3
    if not cfg["ad_account_id"]:
        erros.append("ad_account_id vazio")
    if not cfg["paginas"]:
        erros.append("nenhuma página em 'paginas'")
    if not cfg["destinos"]:
        avisos.append("nenhum destino em 'destinos' — vai precisar passar --url sempre")
    if cfg["objetivo_padrao"] not in OBJETIVOS:
        erros.append(f"objetivo_padrao deve ser um de {sorted(OBJETIVOS)}")
    if not cfg["pixel_id"]:
        avisos.append("sem pixel_id — objetivos vendas/leads não vão funcionar")
    for d in cfg["destinos"]:
        if not str(d.get("url", "")).startswith("http"):
            erros.append(f"destino '{d.get('apelido')}' precisa de url com https://")
    for e in erros:
        print(f"✗ {e}")
    for a in avisos:
        print(f"! {a}")
    if not erros:
        print(f"✓ Perfil OK ({P.PERFIL_PATH})")
    return 1 if erros else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("comando", choices=["checar", "descobrir", "validar"])
    ap.add_argument("--conta", default=None)
    args = ap.parse_args()
    cfg = P.carregar(exigir_perfil=False)
    try:
        if args.comando == "checar":
            return checar(cfg)
        if args.comando == "descobrir":
            return descobrir(cfg, args.conta or cfg["ad_account_id"] or None)
        return validar(cfg)
    except RuntimeError as e:
        print(f"✗ Erro na API do Meta: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
