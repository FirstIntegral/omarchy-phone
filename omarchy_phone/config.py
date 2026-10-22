"""Last wireless address. One small JSON file, no secrets."""

from __future__ import annotations

import json
from pathlib import Path


def config_file(env: dict[str, str]) -> Path:
    base = env.get("XDG_CONFIG_HOME") or str(Path(env.get("HOME", "")) / ".config")
    return Path(base) / "omarchy-phone" / "last.json"


def load_last(env: dict[str, str]) -> str | None:
    try:
        data = json.loads(config_file(env).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    value = data.get("connect") if isinstance(data, dict) else None
    if isinstance(value, str) and value:
        return value
    return None


def save_last(env: dict[str, str], address: str) -> None:
    path = config_file(env)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"connect": address}) + "\n", encoding="utf-8")
