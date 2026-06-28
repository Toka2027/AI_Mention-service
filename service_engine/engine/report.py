"""Deliverables (STEP 7).

Produces the package the document asks for: a PDF report, CSV master table +
frequency tables, PNG "answer proof" screenshots, the indexing-URL / source-link
lists, a manual submission checklist, a manifest, and a final ZIP.

PDF via fpdf2, screenshots via Pillow; everything else uses the stdlib.
"""

from __future__ import annotations

import csv
import json
import shutil
from collections import OrderedDict
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image, ImageDraw, ImageFont

from .extractor import CAPTURE_FIELDS, MASTER_FIELDS
from .models import ClientInput, Question, ResponseRow

REPORT_DATE = "2026-06-28"


# --- text helpers ------------------------------------------------------------

_REPLACEMENTS = {
    "–": "-", "—": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", " ": " ",
    "•": "*",
}


def _latin1(text: str) -> str:
    """fpdf2 core fonts are latin-1 only; coerce text safely."""
    text = text or ""
    for bad, good in _REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


# --- CSV tables --------------------------------------------------------------

def write_capture_template(rows: list[ResponseRow], questions: list[Question], path: Path) -> None:
    by_id = {q.id: q for q in questions}
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAPTURE_FIELDS)
        w.writeheader()
        for r in rows:
            q = by_id.get(r.question_id)
            w.writerow(
                {
                    "question_id": r.question_id,
                    "question_text": q.text if q else "",
                    "model": r.model,
                    "answer": r.answer,
                    "urls": " | ".join(r.urls),
                    "competitors": " | ".join(r.competitors),
                    "screenshot_filename": r.screenshot_filename,
                    "behavior_notes": r.behavior_notes,
                }
            )


def write_questions_csv(questions: list[Question], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "category", "keyword", "question"])
        for q in questions:
            w.writerow([q.id, q.category, q.keyword, q.text])


def write_tables(
    master_table: list[dict],
    src_freq: "OrderedDict[str, int]",
    comp_freq: "OrderedDict[str, int]",
    out_dir: Path,
) -> None:
    with (out_dir / "master_table.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=MASTER_FIELDS)
        w.writeheader()
        w.writerows(master_table)
    with (out_dir / "source_frequency.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["url", "count"])
        for url, n in src_freq.items():
            w.writerow([url, n])
    with (out_dir / "competitor_frequency.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["competitor", "count"])
        for name, n in comp_freq.items():
            w.writerow([name, n])


def write_links(master_table: list[dict], pages_urls: list[str], out_dir: Path) -> None:
    """The 'links' deliverable: created indexing URLs + extracted source links."""
    (out_dir / "indexing_urls.txt").write_text("\n".join(pages_urls) + "\n", encoding="utf-8")
    # Source links extracted from the captured answers.
    links: "OrderedDict[str, int]" = OrderedDict()
    for row in master_table:
        for u in (row.get("urls_extracted") or "").split(" | "):
            u = u.strip()
            if u:
                links[u] = links.get(u, 0) + 1
    with (out_dir / "source_links.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source_url", "times_mentioned"])
        for u, n in links.items():
            w.writerow([u, n])


# --- statistics for the report ----------------------------------------------

def _report_stats(master_table: list[dict]) -> dict:
    captured = [r for r in master_table if r["answer_excerpt"] != ResponseRow.PENDING]
    pending = [r for r in master_table if r["answer_excerpt"] == ResponseRow.PENDING]
    brand_hits = [r for r in captured if r["brand_appeared"] == "Y"]
    models_captured = sorted({r["model"] for r in captured})
    models_pending = sorted({r["model"] for r in pending} - set(models_captured))
    keywords = sorted({r["keyword"] for r in master_table})
    questions = sorted({r["question_id"] for r in master_table})
    return {
        "n_questions": len(questions),
        "n_captures_total": len(master_table),
        "n_captured": len(captured),
        "n_pending": len(pending),
        "n_brand_hits": len(brand_hits),
        "models_captured": models_captured,
        "models_pending": models_pending,
        "keywords": keywords,
    }


def _recommendations(stats: dict, comp_freq: "OrderedDict[str, int]") -> list[str]:
    recs: list[str] = []
    if stats["n_captured"] == 0:
        recs.append(
            "No answers captured yet - run STEP 3 on the in-scope models and re-run the engine."
        )
    else:
        rate = stats["n_brand_hits"] / max(stats["n_captured"], 1)
        if stats["n_brand_hits"] == 0:
            recs.append(
                "The brand did not appear in any captured answer. This is the expected baseline "
                "for a new brand and is exactly the gap this service closes - keep seeding and "
                "re-measure on the next cycle."
            )
        elif rate < 0.34:
            recs.append(
                f"The brand appeared in {stats['n_brand_hits']} of {stats['n_captured']} captured "
                "answers. Prioritise the question categories where it surfaced and repeat them across cycles."
            )
        else:
            recs.append(
                f"Strong early signal: brand appeared in {stats['n_brand_hits']} of "
                f"{stats['n_captured']} captured answers. Reinforce with more indexing pages on the winning keywords."
            )
    if stats["models_pending"]:
        recs.append(
            "Capture the remaining models to complete the dataset: "
            + ", ".join(stats["models_pending"]) + "."
        )
    if comp_freq:
        top = list(comp_freq.items())[:3]
        recs.append(
            "Add competitive-mapping questions that name the most-cited competitors ("
            + ", ".join(name for name, _ in top)
            + ") to position the brand directly against them."
        )
    recs.append(
        "Re-run the seeding cycle periodically; the document notes this is a slow but strong "
        "medium-term effect on how LLMs associate the brand with its keywords."
    )
    return recs


# --- PDF report --------------------------------------------------------------

def render_pdf_report(
    ci: ClientInput,
    master_table: list[dict],
    src_freq: "OrderedDict[str, int]",
    comp_freq: "OrderedDict[str, int]",
    pages_urls: list[str],
    out_path: Path,
    report_date: str = REPORT_DATE,
) -> None:
    stats = _report_stats(master_table)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    def _mc(text, h, wrapmode="WORD"):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            0, h, _latin1(text),
            new_x=XPos.LMARGIN, new_y=YPos.NEXT, wrapmode=wrapmode,
        )

    def h1(t):
        pdf.set_font("Helvetica", "B", 18)
        _mc(t, 9)
        pdf.ln(2)

    def h2(t):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 13)
        _mc(t, 7)
        pdf.ln(1)

    def body(t):
        pdf.set_font("Helvetica", "", 11)
        _mc(t, 6)

    def bullet(t):
        pdf.set_font("Helvetica", "", 11)
        # CHAR wrap so long unbreakable tokens (URLs) never overflow the cell.
        _mc("- " + t, 6, wrapmode="CHAR")

    # Cover
    h1("AI Mention - LLM Query Seeding")
    body(f"Client report for: {ci.brand}")
    body(f"Website: {ci.website}")
    body(f"Package: {ci.package} (${ci.pkg.price_usd})")
    body(f"Niche: {ci.niche}")
    body(f"Report date: {report_date}")

    # Summary
    h2("1. Summary")
    bullet(f"Questions seeded: {stats['n_questions']}")
    bullet(f"Models in scope: {', '.join(ci.pkg.models)}")
    bullet(f"Captures collected: {stats['n_captured']} of {stats['n_captures_total']} (questions x models)")
    bullet(f"Models captured: {', '.join(stats['models_captured']) or 'none'}")
    bullet(f"Models pending (manual STEP 3): {', '.join(stats['models_pending']) or 'none'}")
    bullet(f"Brand appearances in captured answers: {stats['n_brand_hits']}")
    bullet(f"Indexing pages created: {len(pages_urls)}")

    # Keywords
    h2("2. Keywords used")
    for kw in ci.keywords:
        bullet(kw)

    # Competitors
    h2("3. Competitors mentioned by the AI")
    if comp_freq:
        for name, n in comp_freq.items():
            bullet(f"{name} - {n}")
    else:
        body("No competitors were recorded in the captured answers.")

    # Links
    h2("4. Links used by the AI")
    if src_freq:
        body(f"{len(src_freq)} distinct source URL(s) referenced:")
        for url, n in list(src_freq.items())[:40]:
            bullet(f"{url} - {n}")
    else:
        body("No source links were referenced in the captured answers.")

    # Brand appearance detail
    h2("5. Brand appearance by question")
    hits = [r for r in master_table if r["brand_appeared"] == "Y"]
    if hits:
        for r in hits:
            bullet(f"Q{r['question_id']} [{r['model']}] {r['keyword']}: appeared")
    else:
        body("The brand did not explicitly appear in any captured answer (baseline state).")

    # Recommendations
    h2("6. Recommendations for future prompts")
    for rec in _recommendations(stats, comp_freq):
        bullet(rec)

    # Methodology
    h2("7. Methodology & notes")
    body(
        "Questions are generated from the documented brand-focused templates (brand + keyword + "
        "niche context). LLM answers are captured manually by the delivery team (STEP 3); for this "
        "report, Claude answers were captured directly. URLs are auto-extracted from answers; "
        "competitors are recorded from the captured answers. Brand appearance is a literal "
        "case-insensitive match of the brand and its variations."
    )

    pdf.output(str(out_path))


# --- PNG "answer proof" screenshots -----------------------------------------

def _load_font(size: int):
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10
    except TypeError:
        return ImageFont.load_default()


def _wrap(draw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for word in words:
            trial = (cur + " " + word).strip()
            if draw.textlength(trial, font=font) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def render_screenshot(
    question: Question,
    response: ResponseRow,
    ci: ClientInput,
    out_path: Path,
    report_date: str = REPORT_DATE,
) -> None:
    """Render a branded 'answer proof' PNG for a captured answer."""
    W, margin = 1000, 40
    title_font = _load_font(22)
    label_font = _load_font(16)
    body_font = _load_font(16)

    tmp = Image.new("RGB", (W, 10))
    d = ImageDraw.Draw(tmp)
    body_lines = _wrap(d, response.answer, body_font, W - 2 * margin)
    q_lines = _wrap(d, question.text, label_font, W - 2 * margin)

    line_h = 22
    header_h = 110
    height = header_h + (len(q_lines) + len(body_lines)) * line_h + 120
    img = Image.new("RGB", (W, height), "white")
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, W, 70], fill=(20, 30, 60))
    draw.text((margin, 22), f"AI Mention - {response.model} answer", font=title_font, fill="white")

    y = 90
    draw.text((margin, y), f"Brand: {ci.brand}   |   Keyword: {question.keyword}", font=label_font, fill=(60, 60, 60))
    y += line_h + 6
    draw.text((margin, y), "Question:", font=label_font, fill=(20, 30, 60))
    y += line_h
    for ln in q_lines:
        draw.text((margin, y), ln, font=label_font, fill=(0, 0, 0))
        y += line_h
    y += 8
    draw.text((margin, y), "Answer:", font=label_font, fill=(20, 30, 60))
    y += line_h
    for ln in body_lines:
        draw.text((margin, y), ln, font=body_font, fill=(0, 0, 0))
        y += line_h

    footer = f"Captured from {response.model} on {report_date}  |  {ci.website}"
    draw.text((margin, height - 36), footer, font=label_font, fill=(120, 120, 120))
    img.save(out_path)


def write_screenshots(
    questions: list[Question],
    responses: list[ResponseRow],
    ci: ClientInput,
    shots_dir: Path,
    report_date: str = REPORT_DATE,
) -> tuple[int, list[str]]:
    """Render proof PNGs for captured answers; list expected manual captures."""
    shots_dir.mkdir(parents=True, exist_ok=True)
    by_id = {q.id: q for q in questions}
    made = 0
    expected: list[str] = []
    for r in responses:
        q = by_id.get(r.question_id)
        if q is None:
            continue
        if r.is_captured:
            name = r.screenshot_filename or f"q{r.question_id}_{r.model.lower()}.png"
            render_screenshot(q, r, ci, shots_dir / name, report_date)
            made += 1
        else:
            expected.append(r.screenshot_filename or f"q{r.question_id}_{r.model.lower()}.png")
    note = [
        "Screenshots still required from the manual STEP 3 (one PNG per file below).",
        "Save each capture into this folder using the exact filename:",
        "",
        *expected,
    ]
    (shots_dir / "EXPECTED_FILES.txt").write_text("\n".join(note) + "\n", encoding="utf-8")
    return made, expected


# --- checklist, manifest, zip ------------------------------------------------

def write_submission_checklist(ci: ClientInput, pages_urls: list[str], out_dir: Path) -> None:
    lines = [
        f"# Submission & Indexing Checklist - {ci.brand}",
        "",
        "STEP 6 (Fast Indexing) is performed manually. Confirm each item:",
        "",
        "- [ ] Host the indexing pages from `pages/` on the brand site or a controlled domain.",
        "- [ ] Publish `sitemap.xml` and submit it (e.g. Google/Bing webmaster tools).",
        "- [ ] Ping / request crawl for the new URLs.",
        "- [ ] Verify internal links resolve between the published pages.",
        "- [ ] Record the live URLs and the submission confirmation below.",
        "",
        "## Created indexing URLs",
        *[f"- {u}" for u in pages_urls],
        "",
        "## Submission confirmation (fill in)",
        "- Submitted by: ______________________   Date: ____________",
        "- Sitemap submitted to: ______________________",
        "- Indexing/crawl request status: ______________________",
        "",
    ]
    (out_dir / "submission_checklist.md").write_text("\n".join(lines), encoding="utf-8")


def write_manifest(out_dir: Path) -> dict:
    files = []
    for p in sorted(out_dir.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            files.append(
                {"path": str(p.relative_to(out_dir)).replace("\\", "/"), "bytes": p.stat().st_size}
            )
    manifest = {"client_output": out_dir.name, "file_count": len(files), "files": files}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def assemble_zip(out_dir: Path) -> str:
    """Zip the deliverable folder next to it (STEP 7 'clean ZIP folder')."""
    base = out_dir.parent / f"{out_dir.name}_deliverable"
    archive = shutil.make_archive(str(base), "zip", root_dir=str(out_dir))
    return archive
