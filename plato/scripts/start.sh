#!/usr/bin/env bash
# Start PLATO (API + web app). Ctrl+C stops both.
#   ./scripts/start.sh          only this computer can connect (127.0.0.1)
#   ./scripts/start.sh --lan    devices on your network (phones, tablets, other PCs) can connect too
# Ports: PLATO_API_PORT (default 8000), PLATO_WEB_PORT (default 3000).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv"
HOST="127.0.0.1"
[ "${1:-}" = "--lan" ] && HOST="0.0.0.0"
API_PORT="${PLATO_API_PORT:-8000}"
WEB_PORT="${PLATO_WEB_PORT:-3000}"

[ -x "$VENV/bin/python" ] || { echo "Not installed yet. Run: $ROOT/scripts/install.sh" >&2; exit 1; }
[ -f "$ROOT/frontend/.next/standalone/server.js" ] || { echo "Web app not built. Run: $ROOT/scripts/install.sh" >&2; exit 1; }

pids=()
cleanup() {
  trap - INT TERM EXIT
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
  echo; echo "PLATO stopped."
}
trap cleanup INT TERM EXIT

( cd "$ROOT/backend" && exec "$VENV/bin/python" -m uvicorn app.main:app --host "$HOST" --port "$API_PORT" ) &
pids+=($!)
( cd "$ROOT/frontend/.next/standalone" && HOSTNAME="$HOST" PORT="$WEB_PORT" NODE_ENV=production exec node server.js ) &
pids+=($!)

for _ in $(seq 1 60); do
  if "$VENV/bin/python" -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:$API_PORT/api/health', timeout=1)" 2>/dev/null; then
    break
  fi
  sleep 0.5
done

printf '\n\033[96mPLATO is running\033[0m\n  Open:   http://localhost:%s\n' "$WEB_PORT"
if [ "$HOST" = "0.0.0.0" ]; then
  ips="$( (hostname -I 2>/dev/null || ipconfig getifaddr en0 2>/dev/null || true) | tr ' ' '\n' | grep -E '^[0-9]+\.' || true)"
  for ip in $ips; do printf '  Phone/tablet on the same Wi-Fi:  http://%s:%s\n' "$ip" "$WEB_PORT"; done
  printf '  \033[93mAnyone on this network can reach the sign-in page. Use only on networks you trust.\033[0m\n'
fi
printf '  API:    http://localhost:%s/docs\n  Stop:   Ctrl+C\n\n' "$API_PORT"
wait
