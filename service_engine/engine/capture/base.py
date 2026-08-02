"""Capture result type shared by capturers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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
    # --- provenance of a real browser capture (written to q{id}.capture.json) ---
    submitted_prompt: str = ""
    page_url: str = ""
    captured_at: str = ""
    browser: str = ""
    screenshot_bytes: int = 0
    screenshot_width: int = 0
    screenshot_height: int = 0

    def provenance(self) -> dict:
        """The audit record proving this answer came from a real LLM UI."""
        return {
            "question_id": self.question_id,
            "model": self.model,
            "evidence_type": self.evidence_type,
            "captured_at": self.captured_at,
            "page_url": self.page_url,
            "browser": self.browser,
            "submitted_prompt": self.submitted_prompt,
            "answer_chars": len(self.answer or ""),
            "urls_found": len(self.urls),
            "screenshot": Path(self.screenshot_path).name if self.screenshot_path else "",
            "screenshot_bytes": self.screenshot_bytes,
            "screenshot_width": self.screenshot_width,
            "screenshot_height": self.screenshot_height,
        }
