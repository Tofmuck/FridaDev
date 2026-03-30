#!/usr/bin/env bash
set -euo pipefail

# run.sh — wrapper operatoire local pour lancer FridaDev depuis le repo.
# Entree canonique runtime container: Dockerfile -> `python server.py`.

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$APP_DIR/.." && pwd)"
cd "$APP_DIR"

if [[ -f ".env" ]]; then
  # charge .env (sans exporter les commentaires)
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

resolve_python_bin() {
  if [[ -n "${FRIDA_PYTHON_BIN:-}" ]]; then
    printf '%s\n' "$FRIDA_PYTHON_BIN"
    return 0
  fi

  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/bin/python"
    return 0
  fi

  if [[ -x "$APP_DIR/venv/bin/python" ]]; then
    printf '%s\n' "$APP_DIR/venv/bin/python"
    return 0
  fi

  command -v python3
}

PYTHON_BIN="$(resolve_python_bin)"
PORT="${FRIDA_WEB_PORT:-8089}"
HOST="${FRIDA_WEB_HOST:-0.0.0.0}"

echo "== FridaDev =="
echo "APP: $APP_DIR"
echo "REPO: $REPO_ROOT"
echo "PYTHON: $PYTHON_BIN"
echo "HOST: $HOST"
echo "PORT: $PORT"
echo

exec "$PYTHON_BIN" server.py
