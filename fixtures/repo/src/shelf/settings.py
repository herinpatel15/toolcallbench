"""Load the library settings."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "settings.json"


def load_settings(path: Path | None = None) -> dict:
    with open(path or DEFAULT_PATH, encoding="utf-8") as handle:
        return json.load(handle)
