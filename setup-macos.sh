#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else "Python 3.11 or newer is required.")'
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
command -v npm >/dev/null || {
    printf '%s\n' "Node.js/npm is required for the locked HTTPS tunnel runtime." >&2
    exit 1
}
npm ci --omit=dev --ignore-scripts
.venv/bin/python main.py --diagnose

printf '%s\n' "Setup complete. Start the scanner with ./run-macos.sh"
