"""Persistent browser profile per model.

The operator logs in manually the first time; the session (cookies/localStorage)
persists in this profile dir for subsequent runs. No credentials are stored by the
engine; nothing is bypassed.
"""

from __future__ import annotations

from pathlib import Path


def profile_dir(model: str) -> Path:
    d = Path.home() / ".aimention" / "sessions" / model.lower()
    d.mkdir(parents=True, exist_ok=True)
    return d
