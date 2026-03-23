#!/usr/bin/env bash
set -euo pipefail

# run.sh — lance FridaDev (Flask) depuis le dossier du projet.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -f ".env" ]]; then
  # charge .env (sans exporter les commentaires)
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

if [[ -d "venv" ]]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
fi

PORT="${FRIDA_WEB_PORT:-8089}"
HOST="${FRIDA_WEB_HOST:-0.0.0.0}"

echo "== FridaDev =="
echo "ROOT: $ROOT_DIR"
echo "HOST: $HOST"
echo "PORT: $PORT"
echo

exec python3 server.py
