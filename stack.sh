#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
PROJECT_NAME="fridadev"
SERVICE_NAME="fridadev"
LOCAL_URL="http://127.0.0.1:8093/"

usage() {
  cat <<'EOF'
Usage: ./stack.sh <command>

Commands:
  up        Build and start FridaDev
  down      Stop FridaDev
  restart   Rebuild and restart FridaDev
  logs      Follow FridaDev logs
  ps        Show FridaDev status
  config    Render effective docker compose config
  health    Check HTTP health of FridaDev
EOF
}

compose() {
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" "$@"
}

cmd="${1:-ps}"

case "$cmd" in
  up)
    compose up -d --build "$SERVICE_NAME"
    ;;
  down)
    compose down
    ;;
  restart)
    compose up -d --build "$SERVICE_NAME"
    ;;
  logs)
    compose logs -f "$SERVICE_NAME"
    ;;
  ps)
    compose ps
    ;;
  config)
    compose config
    ;;
  health)
    curl -fsS "$LOCAL_URL" >/dev/null
    echo "FridaDev: healthy"
    ;;
  *)
    usage
    exit 1
    ;;
esac
