"""
Global user settings, persisted to settings.json in the project root.
Currently just the Storage Manager's auto-clean toggle, but this is
the one place any future global on/off preference should live.
"""

import json

import config

SETTINGS_PATH = config.DATA_FOLDER / "settings.json"

DEFAULTS = {
    "auto_clean_source_video": False,
}


def _load() -> dict:
    if not SETTINGS_PATH.exists():
        return dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULTS)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)


def _save(data: dict):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get(key: str):
    return _load().get(key, DEFAULTS.get(key))


def set(key: str, value):
    data = _load()
    data[key] = value
    _save(data)


def toggle(key: str) -> bool:
    """Flips a boolean setting and returns the new value."""
    current = bool(get(key))
    new_value = not current
    set(key, new_value)
    return new_value
