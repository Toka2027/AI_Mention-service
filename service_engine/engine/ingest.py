"""Answer ingestion (operator-assisted, minimal effort).

The operator drops raw model answers as plain-text files in a per-model folder; the
engine ingests them into the master responses CSV (auto-extracting URLs), so nobody
edits the CSV or assembles the report by hand.

Drop-folder layout (one file per question per model):
    inputs/captures/<client-slug>/<order-id>/<model>/q{id}.txt          (required: the answer text)
    inputs/captures/<client-slug>/<order-id>/<model>/q{id}.urls.txt     (optional: extra URLs, one per line)
    inputs/captures/<client-slug>/<order-id>/<model>/q{id}.competitors.txt (optional: competitors, one per line)
    inputs/captures/<client-slug>/<order-id>/<model>/q{id}.notes.txt    (optional: behaviour notes)

`<model>` is lower-case (chatgpt, gemini, claude, perplexity). Screenshots are handled
separately via inputs/screenshots/<slug>/<order-id>/ (see report.write_screenshots).
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from . import report
from .extractor import extract_urls, load_responses
from .generator import build_capture_template
from .models import ClientInput, Question


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def _lines(text: str) -> list[str]:
    out: list[str] = []
    for part in text.replace("|", "\n").splitlines():
        part = part.strip()
        if part and part not in out:
            out.append(part)
    return out


def ingest_captures(
    ci: ClientInput,
    questions: list[Question],
    responses_path: str | Path,
    captures_dir: str | Path,
) -> dict:
    """Merge per-model answer drop-files into the responses CSV. Returns per-model
    counts of answers filled this pass. Existing captures (e.g. Claude) are preserved;
    only rows with a matching drop-file are updated."""
    rp = Path(responses_path)
    captures = Path(captures_dir)

    rows = load_responses(rp) if rp.exists() else build_capture_template(questions, ci.pkg.models)
    idx = {(r.question_id, r.model.lower()): r for r in rows}

    stats: "OrderedDict[str, int]" = OrderedDict((m, 0) for m in ci.pkg.models)
    for model in ci.pkg.models:
        mdir = captures / model.lower()
        if not mdir.exists():
            continue
        for q in questions:
            answer = _read(mdir / f"q{q.id}.txt")
            if not answer:
                continue
            row = idx.get((q.id, model.lower()))
            if row is None:
                continue
            row.answer = answer
            merged: "OrderedDict[str, None]" = OrderedDict()
            for u in [*_lines(_read(mdir / f"q{q.id}.urls.txt")), *extract_urls(answer)]:
                merged.setdefault(u, None)
            row.urls = list(merged.keys())
            comps = _lines(_read(mdir / f"q{q.id}.competitors.txt"))
            if comps:
                row.competitors = comps
            notes = _read(mdir / f"q{q.id}.notes.txt")
            if notes:
                row.behavior_notes = notes
            # Provenance: a browser runner writes q{id}.evidence.txt (=browser); a human
            # dropping files without one is treated as operator-assisted capture.
            ev = _read(mdir / f"q{q.id}.evidence.txt").lower()
            row.evidence_type = ev if ev else "operator"
            stats[model] += 1

    report.write_capture_template(rows, questions, rp)
    return stats


def write_prompt_packet(ci: ClientInput, questions: list[Question], captures_dir: str | Path) -> int:
    """Write one prompt file per question per model into the drop-folder, so the
    operator/browser-runner has the exact prompt to submit. Returns files written."""
    captures = Path(captures_dir)
    written = 0
    for model in ci.pkg.models:
        mdir = captures / model.lower()
        mdir.mkdir(parents=True, exist_ok=True)
        for q in questions:
            (mdir / f"q{q.id}.prompt.txt").write_text(q.text, encoding="utf-8")
            written += 1
    return written
