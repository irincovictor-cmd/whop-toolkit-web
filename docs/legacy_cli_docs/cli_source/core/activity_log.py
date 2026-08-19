"""
Global session memory.

A single activity_log.json in the project root, separate from any
one video's project folder. Every completed action gets appended
here. On boot, whop.py reads the last few entries and prints a
"Welcome back" message so the user remembers where they left off.
"""

import json
from datetime import datetime

import config

LOG_PATH = config.DATA_FOLDER / "activity_log.json"

MAX_ENTRIES_KEPT = 200  # trim the file so it never grows forever


def _load() -> list:
    if not LOG_PATH.exists():
        return []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries: list):
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries[-MAX_ENTRIES_KEPT:], f, indent=2, ensure_ascii=False)


def log_activity(description: str, project_title: str = None):
    """
    Append one entry. Call this after any action completes
    successfully (transcript made, scenes found, clip cropped, etc).
    """
    entries = _load()
    entries.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description,
        "project": project_title,
    })
    _save(entries)


def get_recent(n: int = 3) -> list:
    entries = _load()
    return entries[-n:][::-1]  # most recent first


def print_welcome_message():
    recent = get_recent(3)
    if not recent:
        print("Welcome to Whop Toolkit! This looks like your first run.")
        return

    print("Welcome back! Last session you:")
    for entry in recent:
        who = f" ({entry['project']})" if entry.get("project") else ""
        print(f"  - [{entry['timestamp']}] {entry['description']}{who}")
    print()
