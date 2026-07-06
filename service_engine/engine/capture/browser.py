"""Playwright browser capturer (human-in-the-loop).

Launches a real Chrome/Chromium with a persistent profile, lets the operator log in
manually, then for each prompt: submits it, waits for the answer, and captures the
answer text + a REAL full-page screenshot. Playwright is imported lazily so the rest
of the engine has no hard dependency on it.
"""

from __future__ import annotations

from pathlib import Path

from ..extractor import extract_urls
from .base import CaptureResult
from .selectors import MODELS
from .session import profile_dir


class PlaywrightCapturer:
    def __init__(self, model: str, headful: bool = True, login_wait: bool = True, timeout_ms: int = 120000):
        self.model = model.lower()
        self.cfg = MODELS.get(self.model)
        if not self.cfg:
            raise ValueError(f"No selector config for model '{model}' (see engine/capture/selectors.py)")
        self.headful = headful
        self.login_wait = login_wait
        self.timeout = timeout_ms
        self._pw = None
        self._ctx = None
        self.page = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright  # lazy
        self._pw = sync_playwright().start()
        self._ctx = self._pw.chromium.launch_persistent_context(
            str(profile_dir(self.model)), headless=not self.headful
        )
        self.page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        self.page.goto(self.cfg["url"])
        if self.login_wait:
            input(f"[{self.model}] Log in / accept any consent in the browser window, "
                  f"then press Enter here to begin capture...")
        return self

    def __exit__(self, *exc):
        try:
            if self._ctx:
                self._ctx.close()
        finally:
            if self._pw:
                self._pw.stop()

    def capture(self, question_id: int, prompt: str, screenshot_path: Path) -> CaptureResult:
        try:
            page = self.page
            box = page.locator(self.cfg["input"]).first
            box.click()
            try:
                box.fill(prompt)
            except Exception:
                box.type(prompt)
            page.keyboard.press("Enter")
            # Best-effort wait for the generation-done signal, then operator confirm.
            done = self.cfg.get("done")
            if done:
                try:
                    page.wait_for_selector(done, timeout=self.timeout)
                except Exception:
                    pass
            input(f"[{self.model} q{question_id}] Press Enter when the answer has fully rendered...")
            answer = page.locator(self.cfg["answer"]).last.inner_text().strip()
            Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot_path), full_page=True)
            return CaptureResult(
                question_id, self.model, ok=bool(answer), answer=answer,
                urls=extract_urls(answer), screenshot_path=str(screenshot_path),
                evidence_type="browser",
            )
        except Exception as exc:  # noqa: BLE001 - never fabricate; record + continue
            return CaptureResult(question_id, self.model, ok=False, notes=f"capture error: {exc!r}")
