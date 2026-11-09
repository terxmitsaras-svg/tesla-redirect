#!/usr/bin/env bash
# PLATO installer for Linux (Ubuntu, Debian, Kali, Fedora, Arch…), macOS, and Chromebook (Linux dev environment).
#   ./scripts/install.sh            install API, web app and the `plato` CLI
#   PLATO_PYTHON=python3.12 ./scripts/install.sh   use a specific Python
# Safe to re-run: it updates dependencies and keeps your existing .env and database.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv"
cyan() { printf '\033[96m%s\033[0m\n' "$*"; }
ok() { printf '\033[92m✓ %s\033[0m\n' "$*"; }
die() { printf '\033[91m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- platform
OS="linux"; DISTRO="linux"
case "$(uname -s)" in
  Darwin) OS="macos"; DISTRO="macos" ;;
  Linux)
    if [ -f /etc/os-release ]; then . /etc/os-release; DISTRO="${ID:-linux}"; fi
    if [ -e /dev/.cros_milestone ] || [ "$(hostname 2>/dev/null)" = "penguin" ]; then DISTRO="chromeos"; fi ;;
  *) die "Unsupported OS $(uname -s). On Windows use scripts\\install.ps1 in PowerShell." ;;
esac
cyan "PLATO installer · $DISTRO"

hint() {
  case "$DISTRO" in
    macos) echo "  brew install python@3.12 node" ;;
    kali|debian|ubuntu|linuxmint|pop|chromeos)
      echo "  sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
      echo "  Node.js 20+: https://nodejs.org (or: curl -fsSL https://fnm.vercel.app/install | bash && fnm install 22)" ;;
    fedora|rhel|centos) echo "  sudo dnf install -y python3 nodejs npm" ;;
    arch|manjaro|endeavouros) echo "  sudo pacman -S --needed python nodejs npm" ;;
    *) echo "  Install Python 3.11+ and Node.js 20.9+ with your package manager." ;;
  esac
}

# ---------------------------------------------------------------- Python ≥ 3.11
PY=""
for cand in ${PLATO_PYTHON:-} python3.13 python3.12 python3.11 python3; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    PY="$(command -v "$cand")"; break
  fi
done
[ -n "$PY" ] || { echo "Python 3.11+ is required. Install it:"; hint; exit 1; }
"$PY" -c 'import venv, ensurepip' 2>/dev/null || { echo "Python venv support is missing:"; hint; exit 1; }
ok "Python $("$PY" -c 'import platform; print(platform.python_version())') ($PY)"

# ---------------------------------------------------------------- Node ≥ 20.9
command -v node >/dev/null 2>&1 || { echo "Node.js 20.9+ is required:"; hint; exit 1; }
node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>20||(a===20&&b>=9)?0:1)' \
  || { echo "Node.js $(node -v) is too old; 20.9+ is required:"; hint; exit 1; }
ok "Node.js $(node -v)"

# ---------------------------------------------------------------- backend + CLI
cyan "Installing the API and the plato CLI into $VENV"
[ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --upgrade pip
"$VENV/bin/python" -m pip install -q -r "$ROOT/backend/requirements.txt"
"$VENV/bin/python" -m pip install -q "$ROOT/cli"
ok "API and CLI installed"

# ---------------------------------------------------------------- web app
cyan "Building the web app"
( cd "$ROOT/frontend" && npm ci --no-audit --no-fund --loglevel=error && NEXT_TELEMETRY_DISABLED=1 npm run build >/dev/null )
ok "Web app built"

# ---------------------------------------------------------------- configuration
if [ ! -f "$ROOT/.env" ]; then
  "$VENV/bin/python" - "$ROOT" <<'PYEOF'
import secrets, sys
from pathlib import Path
from cryptography.fernet import Fernet
root = Path(sys.argv[1])
text = (root / ".env.example").read_text(encoding="utf-8")
text = text.replace("PLATO_JWT_SECRET=change-me-to-a-long-random-string", f"PLATO_JWT_SECRET={secrets.token_urlsafe(48)}")
text = text.replace("PLATO_ENCRYPTION_KEY=\n", f"PLATO_ENCRYPTION_KEY={Fernet.generate_key().decode()}\n", 1)
text += f"\n# Local database (created by the installer)\nPLATO_DATABASE_URL=sqlite+aiosqlite:///{(root / 'plato.db').as_posix()}\n"
env = root / ".env"
env.write_text(text, encoding="utf-8")
env.chmod(0o600)
PYEOF
  ok "Created .env with fresh secrets (keep it private)"
else
  ok "Kept existing .env"
fi

cat <<EOF

$(cyan "PLATO is installed.")
  Start:          $ROOT/scripts/start.sh            (this computer only)
                  $ROOT/scripts/start.sh --lan      (also phones/tablets on your Wi-Fi)
  Terminal app:   $VENV/bin/plato --help
                  (add to PATH:  export PATH="$VENV/bin:\$PATH")
EOF
