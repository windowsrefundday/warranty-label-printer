# Architecture

The application is a Python program with optional Node.js support for the HTTPS
tunnel runtime. Source checkouts and managed release bundles use the same
`main.py`; the stable launcher selects the active version before composing the
CLI or web interface.

```text
scanner / browser
        |
        v
 CLI or web interface  -->  WarrantyEngine  -->  vendor plugin
        |                         |                    |
        |                         v                    v
        +------------------> printer connector   live vendor portal
                                  |
                                  v
                         virtual file or TSC MB341
```

## Boundaries

- `core/` owns domain models, warranty lookup, caching, label formatting,
  printer contracts, and platform composition.
- `interfaces/` owns user-facing input/output: terminal scanning, HTTP routes,
  browser plugins, and profile operations.
- `tests/` owns standard-library `unittest` coverage and mocks external
  browsers, operating-system printer APIs, and queues.
- `tools/` owns setup orchestration, publication-safety auditing, and the
  signed managed-update launcher. `tools/updater.py` must remain independent of
  application imports so a broken release cannot prevent recovery.
- `.github/` owns automated validation and dependency/security checks.

Keep platform-specific code behind injected discovery and transport contracts.
Shared warranty and TSPL logic must not depend on CUPS, Windows spooler APIs, or
the default printer.
