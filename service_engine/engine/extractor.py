"""Data extraction & master table (STEP 4).

Reads the team-filled capture CSV, auto-extracts URLs from answer text, detects
brand appearances, and assembles the master table plus source/competitor
frequency counts. No LLM calls; competitors are read from what the team entered.
"""

from __future__ import annotations

import csv
import re
from collections import OrderedDict
from pathlib import Path

from .models import ClientInput, Question, ResponseRow

# Capture-file column order (also used when writing the blank template).
CAPTURE_FIELDS = [
    "question_id",
    "question_text",
    "model",
    "answer",
    "urls",
    "competitors",
    "screenshot_filename",
    "behavior_notes",
]

MASTER_FIELDS = [
    "question_id",
    "category",
    "keyword",
    "question_text",
    "model",
    "answer_excerpt",
    "urls_extracted",
    "competitors_mentioned",
    "brand_appeared",
    "notes",
]

_URL_RE = re.compile(r"https?://[^\s)<>\]\"']+", re.IGNORECASE)


def extract_urls(text: str) -> list[str]:
    """Return URLs found in text, de-duplicated, order preserved."""
    if not text:
        return []
    found: "OrderedDict[str, None]" = OrderedDict()
    for raw in _URL_RE.findall(text):
        url = raw.rstrip(".,;:!?")  # strip trailing sentence punctuation
        found.setdefault(url, None)
    return list(found.keys())


def brand_appears(text: str, brand: str, variations: list[str]) -> bool:
    """Case-insensitive literal substring match of the brand or any variation."""
    if not text:
        return False
    haystack = text.lower()
    for term in [brand, *variations]:
        if term and term.lower() in haystack:
            return True
    return False


def _split_pipe(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split("|") if part.strip()]


def load_responses(path: str | Path) -> list[ResponseRow]:
    """Load a filled capture CSV into ResponseRow objects. URLs from the CSV are
    unioned with any URLs auto-extracted from the answer text."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Responses file not found: {p}")
    rows: list[ResponseRow] = []
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            answer = (raw.get("answer") or "").strip()
            csv_urls = _split_pipe(raw.get("urls") or "")
            auto_urls = extract_urls(answer)
            merged: "OrderedDict[str, None]" = OrderedDict()
            for u in [*csv_urls, *auto_urls]:
                merged.setdefault(u, None)
            rows.append(
                ResponseRow(
                    question_id=int(raw.get("question_id") or 0),
                    model=(raw.get("model") or "").strip(),
                    answer=answer,
                    urls=list(merged.keys()),
                    competitors=_split_pipe(raw.get("competitors") or ""),
                    screenshot_filename=(raw.get("screenshot_filename") or "").strip(),
                    behavior_notes=(raw.get("behavior_notes") or "").strip(),
                )
            )
    return rows


def _excerpt(text: str, limit: int = 400) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def build_master_table(
    questions: list[Question],
    responses: list[ResponseRow],
    ci: ClientInput,
) -> list[dict]:
    """Join questions with captured responses into the master table (STEP 4)."""
    by_id = {q.id: q for q in questions}
    table: list[dict] = []
    for r in responses:
        q = by_id.get(r.question_id)
        if q is None:
            continue
        if r.is_captured:
            answer_excerpt = _excerpt(r.answer)
            brand_flag = "Y" if brand_appears(r.answer, ci.brand, ci.brand_variations) else "N"
        else:
            answer_excerpt = ResponseRow.PENDING
            brand_flag = "N/A"
        table.append(
            {
                "question_id": q.id,
                "category": q.category,
                "keyword": q.keyword,
                "question_text": q.text,
                "model": r.model,
                "answer_excerpt": answer_excerpt,
                "urls_extracted": " | ".join(r.urls),
                "competitors_mentioned": " | ".join(r.competitors),
                "brand_appeared": brand_flag,
                "notes": r.behavior_notes,
            }
        )
    return table


def source_frequency(responses: list[ResponseRow]) -> "OrderedDict[str, int]":
    """Count how often each source URL appears across captured answers."""
    freq: "OrderedDict[str, int]" = OrderedDict()
    for r in responses:
        if not r.is_captured:
            continue
        for u in r.urls:
            freq[u] = freq.get(u, 0) + 1
    return OrderedDict(sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])))


def competitor_frequency(responses: list[ResponseRow]) -> "OrderedDict[str, int]":
    """Count how often each competitor brand is named across captured answers."""
    freq: "OrderedDict[str, int]" = OrderedDict()
    for r in responses:
        if not r.is_captured:
            continue
        for c in r.competitors:
            key = c.strip()
            freq[key] = freq.get(key, 0) + 1
    return OrderedDict(sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])))
