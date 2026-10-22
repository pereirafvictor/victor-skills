#!/usr/bin/env bash
# Instala as skills de Meta Ads no Claude Code (Mac/Linux).
# Uso: bash instalar.sh
set -e

ORIGEM="$(cd "$(dirname "$0")" && pwd)"
DESTINO="$HOME/.claude/skills"
CONFIG="$HOME/.meta-ads"
PY="$(command -v python3 || command -v python || true)"

echo ""
echo "== Skills Meta Ads =="
echo ""

if [ -z "$PY" ]; then
  echo "✗ Python não encontrado. Instale em https://www.python.org/downloads/ e rode de novo."
  exit 1
fi

mkdir -p "$DESTINO"
for skill in "$ORIGEM"/skills/*/; do
  nome="$(basename "$skill")"
  rm -rf "$DESTINO/$nome"
  cp -R "$skill" "$DESTINO/$nome"
  echo "✓ skill $nome"
done

"$PY" -m pip install --quiet -r "$ORIGEM/requirements.txt"
echo "✓ dependências Python"

mkdir -p "$CONFIG"
if [ ! -f "$CONFIG/.env" ]; then
  echo "META_ACCESS_TOKEN=" > "$CONFIG/.env"
  chmod 600 "$CONFIG/.env"
  echo "✓ criado $CONFIG/.env (cole seu token nele)"
else
  echo "✓ $CONFIG/.env já existe (mantido)"
fi

echo ""
echo "Pronto! Abra o Claude Code e diga: configura meu meta ads"
echo ""
