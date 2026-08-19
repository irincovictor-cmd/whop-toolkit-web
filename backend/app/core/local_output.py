"""
Local-dev helper: optionally copy finished files into a folder on disk
(e.g. Desktop) so testing does not depend only on the browser download dialog.

Set LOCAL_OUTPUT_DIR in backend/.env, e.g.
  LOCAL_OUTPUT_DIR=C:\\Users\\Victorjames\\Desktop\\whop clips

In production leave unset and use object storage instead.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def get_local_output_dir() -> Path | None:
    raw = os.getenv("LOCAL_OUTPUT_DIR", "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_to_local_output(source: Path, preferred_name: str | None = None) -> Path | None:
    """Copy source into LOCAL_OUTPUT_DIR. Returns destination path or None."""
    out_dir = get_local_output_dir()
    if out_dir is None:
        return None
    name = preferred_name or source.name
    # avoid overwriting: add short suffix if needed
    dest = out_dir / name
    if dest.exists():
        stem, suf = dest.stem, dest.suffix
        dest = out_dir / f"{stem}_{os.urandom(3).hex()}{suf}"
    shutil.copy2(source, dest)
    return dest
