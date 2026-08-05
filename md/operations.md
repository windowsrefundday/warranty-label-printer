# Operations

## Setup and diagnostics

- macOS: `./setup-macos.sh`, then `.venv/bin/python main.py --diagnose`.
- Windows: `.\warranty-windows.ps1 setup`, then
  `.\warranty-windows.ps1 doctor` when troubleshooting.

Setup installs pinned Python dependencies, attempts Chromium, and supports
optional tunnel runtime installation. A blocked Chromium download is reported
as a warning so Windows can use installed Edge or Chrome; dependency and
diagnostic failures remain fatal. A trusted corporate CA may be supplied only
for that browser download stage with `-BrowserCaCert`. Setup does not disable
TLS verification globally. It does not print, calibrate, select a default
printer, or download a driver.

## Runtime modes

- CLI: `python main.py` or the Windows `cli` helper.
- Local web: `python main.py --mode web --port 9191`.
- HTTPS tunnel: add `--tunnel` only after the optional locked localtunnel
  runtime is installed.
- Safe virtual output: select `file` when physical printer validation is not
  complete.

## Managed application updates

The stable launcher in `tools/launcher.py` is deliberately outside the managed
application directory. It stores signed releases under the per-user update
directory, with one immutable directory per version and an atomically replaced
state pointer. The active checkout is never overwritten.

- `check` fetches and verifies the HTTPS manifest and Ed25519 signature.
- `download` verifies the target size and SHA-256 digest, rejects unsafe ZIP
  paths, extracts to staging, and marks the release pending for the next start.
- `status` reports the current, pending, previous, and locally blocked releases.
- `rollback` returns to the previous known-good release without touching cache,
  labels, printer bindings, or profiles.

Normal launcher startup performs a non-blocking signed check when the last check
is at least six hours old. While the application remains open, the launcher
repeats that check every six hours; a downloaded release is staged for the next
launch.

Updates are fail-closed. Expired metadata, unknown signing keys, downgrades,
wrong platforms, corrupt archives, insufficient disk space, and failed startup
probes do not replace the current release. The first managed installation still
requires the existing setup flow so the bootstrap environment is explicit.
Set `WARRANTY_LABEL_DISABLE_AUTO_UPDATE=1` for an offline or centrally managed
machine; manual `check` and `download` commands remain available.

Runtime caches, bindings, profiles, labels, and CSV exports belong in the
per-user application data directory. They must not be copied into the
checkout, committed, or attached to public support requests.
