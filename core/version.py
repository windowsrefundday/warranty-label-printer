"""Application version resolution for source and managed releases."""

from __future__ import annotations

import json
import os
from pathlib import Path


DEVELOPMENT_VERSION = "0.0.0-dev"


def application_version() -> str:
    """Return the immutable release marker or the source-development version."""
    explicit = os.environ.get("WARRANTY_LABEL_APP_VERSION")
    if explicit:
        return explicit
    module_path = Path(__file__).resolve()
    release_root = (
        module_path.parents[2]
        if module_path.parents[1].name == "app"
        else module_path.parents[1]
    )
    marker = release_root / "release.json"
    try:
        document = json.loads(marker.read_text(encoding="utf-8"))
        version = document.get("version")
        if isinstance(version, str) and version:
            return version
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    return DEVELOPMENT_VERSION
