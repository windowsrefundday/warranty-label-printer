# Repository Guidelines

## Project Structure & Module Organization

`main.py` is the application entry point. Shared domain logic lives in `core/`: vendor integrations are under `core/vendors/`, label rendering under `core/label_formatters/`, and modular printer discovery, bindings, profiles, and transports under `core/printers/`. Platform composition belongs in `core/application/composition.py`; keep OS-specific code out of shared TSPL and warranty logic. CLI, web, scanner, and web-plugin code lives in `interfaces/`. Tests are in `tests/` and follow the source module boundaries. Built-in immutable printer profiles are stored in `core/printers/profiles/builtin/`; generated labels and mutable cache/configuration are runtime data, not source assets.

## Setup, Test, and Development Commands

Use the repository scripts from any checkout path:

```bash
./setup-macos.sh          # create .venv, install dependencies/Chromium, diagnose
./run-macos.sh            # launch the CLI on macOS
python main.py --diagnose # read-only environment and printer checks
python main.py --mode web --port 9191
```

For Windows, prefer `.\warranty-windows.ps1 <setup|doctor|printer|safe|cli|web|verify>`;
the lower-level entry points remain `.\setup-windows.ps1` and
`.\run-windows.ps1`.

Before submitting changes, run:

```bash
python -m unittest discover -s tests -v
python -m compileall -q core interfaces main.py tests
npx pyright
```

## Coding Style & Naming Conventions

Use four-space indentation, type annotations, short docstrings for public APIs, and standard Python naming: `snake_case` for functions/modules, `PascalCase` for classes, and `UPPER_CASE` for constants. Prefer dependency injection through protocols such as `PrinterDiscovery` and `RawTransport`; avoid platform checks inside shared business logic. Keep imports explicit and platform-only dependencies lazy or conditional.

## Testing Guidelines

Tests use the standard-library `unittest` framework. Name files `test_<feature>.py` and methods `test_<behavior>`. Mock browser, CUPS, and Windows spooler boundaries. Automated tests must never access a physical printer, change calibration, or depend on a default queue. Cover success and fail-closed behavior, including wrong model/DPI, offline queues, partial writes, and unverified warranty data.

## Commit & Pull Request Guidelines

This checkout contains no Git history, so no existing convention is observable. Use concise imperative commits, for example `Add Windows RAW spooler validation`. Pull requests should explain behavior and safety impact, list macOS/Windows checks run, link relevant issues, and include screenshots only for UI changes.

## Security & Printer Safety

Never commit credentials, local bindings, caches, `.env`, or `.venv`. Preserve explicit queue selection, RAW TSPL submission, one-copy enforcement, and fail-safe virtual output. Do not add automatic retries, default-printer fallback, or setup-time printing/calibration.
