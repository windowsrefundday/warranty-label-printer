# Operations

## Setup and diagnostics

- macOS: `./setup-macos.sh`, then `.venv/bin/python main.py --diagnose`.
- Windows: `.\warranty-windows.ps1 setup`, then
  `.\warranty-windows.ps1 doctor` when troubleshooting.

Setup installs pinned Python dependencies, Chromium, and optional tunnel
runtime support. It does not print, calibrate, select a default printer, or
download a driver.

## Runtime modes

- CLI: `python main.py` or the Windows `cli` helper.
- Local web: `python main.py --mode web --port 9191`.
- HTTPS tunnel: add `--tunnel` only after the optional locked localtunnel
  runtime is installed.
- Safe virtual output: select `file` when physical printer validation is not
  complete.

Runtime caches, bindings, profiles, labels, and CSV exports belong in the
per-user application data directory. They must not be copied into the
checkout, committed, or attached to public support requests.
