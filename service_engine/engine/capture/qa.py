"""Strict QA for real browser captures.

Answers the only question that matters for proof: *did this answer actually come
from a real LLM UI in a real browser?* Every check is mechanical - nothing here
trusts a label. A cell passes only when all of the following hold:

  1. the answer file exists and holds real, non-placeholder text
  2. the evidence marker says exactly `browser`
  3. a provenance record exists (submitted prompt, page URL, UTC capture time)
  4. the submitted prompt matches the question the engine generated
  5. the page URL is on the model's real host (chatgpt.com, gemini.google.com, ...)
  6. the screenshot exists, is a real PNG, and has real browser dimensions

Used by:  python -m engine.main capture-qa ...
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MIN_ANSWER_CHARS = 80
MIN_SHOT_BYTES = 20_000
MIN_SHOT_EDGE = 400

# The real host each model's UI must be served from. A capture whose page URL is
# not on its model's host is not proof of that model.
MODEL_HOSTS = {
    "chatgpt": ("chatgpt.com", "chat.openai.com"),
    "gemini": ("gemini.google.com",),
    "claude": ("claude.ai",),
    "perplexity": ("perplexity.ai", "www.perplexity.ai"),
}

PLACEHOLDER_MARKERS = ("[pending capture]", "proof card", "model-authored")


def _png_size(path: Path) -> tuple[int, int]:
    """Read a PNG's dimensions from its IHDR chunk (no Pillow dependency)."""
    data = path.read_bytes()[:33]
    if len(data) < 24 or not data.startswith(PNG_MAGIC):
        return (0, 0)
    return (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big"))


def verify_capture(
    captures_dir: str | Path,
    shots_dir: str | Path,
    model: str,
    question_ids: list[int],
    question_texts: dict[int, str] | None = None,
) -> dict:
    """Validate the browser evidence for one model over `question_ids`."""
    caps = Path(captures_dir) / model.lower()
    shots = Path(shots_dir)
    qtexts = question_texts or {}
    cells: list[dict] = []

    for qid in question_ids:
        checks: list[tuple[str, str, str]] = []

        def add(name: str, ok: bool, detail: str, soft: bool = False) -> None:
            checks.append((name, PASS if ok else (WARN if soft else FAIL), detail))

        # 1. real answer text
        ans_file = caps / f"q{qid}.txt"
        answer = ans_file.read_text(encoding="utf-8").strip() if ans_file.exists() else ""
        low = answer.lower()
        add("answer file", bool(answer), f"{len(answer)} chars" if answer else f"MISSING {ans_file}")
        if answer:
            add("answer is real text",
                len(answer) >= MIN_ANSWER_CHARS and not any(m in low for m in PLACEHOLDER_MARKERS),
                "real answer text" if len(answer) >= MIN_ANSWER_CHARS
                else f"only {len(answer)} chars (min {MIN_ANSWER_CHARS})")

        # 2. evidence marker
        ev_file = caps / f"q{qid}.evidence.txt"
        ev = ev_file.read_text(encoding="utf-8").strip().lower() if ev_file.exists() else ""
        add("evidence type is 'browser'", ev == "browser", ev or "MISSING")

        # 3-5. provenance record
        prov_file = caps / f"q{qid}.capture.json"
        prov = {}
        if prov_file.exists():
            try:
                prov = json.loads(prov_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                prov = {}
        add("provenance record", bool(prov),
            f"captured_at={prov.get('captured_at', '?')}" if prov else f"MISSING {prov_file.name}")

        if prov:
            submitted = (prov.get("submitted_prompt") or "").strip()
            expected = (qtexts.get(qid) or "").strip()
            if expected:
                add("submitted prompt matches question", submitted == expected,
                    "exact match" if submitted == expected
                    else f"MISMATCH: submitted {submitted[:60]!r}")
            else:
                add("submitted prompt recorded", bool(submitted), submitted[:60] or "empty")

            host = urlparse(prov.get("page_url") or "").netloc.lower()
            allowed = MODEL_HOSTS.get(model.lower(), ())
            add(f"page URL on {model} host",
                bool(host) and any(host == h or host.endswith("." + h) for h in allowed),
                host or "no page_url recorded")

            add("capture timestamp", bool(prov.get("captured_at")),
                prov.get("captured_at") or "missing")

        # 6. real screenshot
        matches = sorted(shots.glob(f"q{qid}_{model.lower()}*.png")) if shots.exists() else []
        if not matches:
            add("screenshot present", False, f"MISSING {shots}/q{qid}_{model.lower()}.png")
        else:
            shot = matches[0]
            size = shot.stat().st_size
            is_png = shot.read_bytes()[:8] == PNG_MAGIC
            w, h = _png_size(shot)
            add("screenshot present", True, f"{shot.name} ({size} bytes)")
            add("screenshot is a real PNG", is_png, "PNG header ok" if is_png else "not a PNG")
            add("screenshot has browser dimensions", w >= MIN_SHOT_EDGE and h >= MIN_SHOT_EDGE,
                f"{w}x{h}" if w else "unreadable")
            add("screenshot size plausible", size >= MIN_SHOT_BYTES,
                f"{size} bytes", soft=size >= MIN_SHOT_BYTES // 4)

        statuses = {s for _, s, _ in checks}
        overall = FAIL if FAIL in statuses else (WARN if WARN in statuses else PASS)
        cells.append({
            "question_id": qid, "model": model.lower(),
            "checks": [{"name": n, "status": s, "detail": d} for n, s, d in checks],
            "overall": overall,
        })

    all_status = {c["overall"] for c in cells}
    overall = FAIL if (FAIL in all_status or not cells) else (WARN if WARN in all_status else PASS)
    return {"model": model.lower(), "captures_dir": str(caps), "shots_dir": str(shots),
            "cells": cells, "overall": overall}


def format_report(result: dict) -> str:
    icon = {PASS: "[PASS]", WARN: "[WARN]", FAIL: "[FAIL]"}
    lines = [
        f"Browser capture QA - model: {result['model']}",
        f"  answers:     {result['captures_dir']}",
        f"  screenshots: {result['shots_dir']}",
        "",
    ]
    for cell in result["cells"]:
        lines.append(f"  Q{cell['question_id']} -> {icon[cell['overall']]}")
        for c in cell["checks"]:
            lines.append(f"    {icon[c['status']]:7} {c['name']}: {c['detail']}")
        lines.append("")
    lines.append(f"OVERALL: {result['overall']}")
    if result["overall"] == FAIL:
        lines.append("=> NOT valid browser proof. Fix the [FAIL] items and re-capture.")
    elif result["overall"] == WARN:
        lines.append("=> Real browser capture, but review the [WARN] items.")
    else:
        lines.append("=> Verified real browser capture (evidence_type=browser).")
    return "\n".join(lines)
