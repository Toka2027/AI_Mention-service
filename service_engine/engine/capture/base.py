"""Capture result type shared by capturers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CaptureResult:
    question_id: int
    model: str
    ok: bool
    answer: str = ""
    urls: list[str] = field(default_factory=list)
    screenshot_path: str = ""
    evidence_type: str = "browser"
    notes: str = ""
