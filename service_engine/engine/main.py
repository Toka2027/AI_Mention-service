"""Command-line entry point for the AI Mention engine.

Single `run` command that walks the documented workflow:
  STEP 1 validate input -> STEP 2 questions -> STEP 3 capture template/plan ->
  (with responses) STEP 4 master table -> STEP 5 pages -> STEP 6 sitemap ->
  STEP 7 deliverables.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import extractor, generator, pages, report
from .models import ClientInput, Question, ResponseRow


def _pick_page_response(question: Question, responses: list[ResponseRow]) -> ResponseRow | None:
    """Choose which captured answer to feature on a page: prefer a captured one."""
    matches = [r for r in responses if r.question_id == question.id]
    if not matches:
        return None
    for r in matches:
        if r.is_captured:
            return r
    return matches[0]


def run(input_path: str, responses_path: str | None, out_root: str) -> Path:
    ci = ClientInput.from_json(input_path)
    for w in ci.warnings:
        print(f"  ! warning: {w}")

    pkg = ci.pkg
    out_dir = Path(out_root) / pages.slugify(ci.brand)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Client: {ci.brand}  |  Package: {pkg.name}  |  Models: {', '.join(pkg.models)}")

    # --- STEP 2: question set ----------------------------------------------
    questions = generator.generate_questions(ci, pkg.n_questions)
    report.write_questions_csv(questions, out_dir / "questions.csv")
    (out_dir / "questions.json").write_text(
        json.dumps([q.__dict__ for q in questions], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"STEP 2  generated {len(questions)} questions -> questions.csv / questions.json")

    # --- STEP 3: capture template + query plan -----------------------------
    capture_rows = generator.build_capture_template(questions, pkg.models)
    report.write_capture_template(capture_rows, questions, out_dir / "responses_template.csv")
    (out_dir / "query_plan.md").write_text(
        generator.build_query_plan(ci, questions, pkg.models), encoding="utf-8"
    )
    print(f"STEP 3  wrote capture template ({len(capture_rows)} rows) + query_plan.md")

    has_responses = bool(responses_path)
    responses = extractor.load_responses(responses_path) if has_responses else capture_rows

    # --- STEP 4: master table & frequencies --------------------------------
    master = extractor.build_master_table(questions, responses, ci)
    src_freq = extractor.source_frequency(responses)
    comp_freq = extractor.competitor_frequency(responses)
    report.write_tables(master, src_freq, comp_freq, out_dir)
    print(f"STEP 4  master_table.csv ({len(master)} rows) + frequency tables")

    # --- STEP 5: indexing pages --------------------------------------------
    page_questions = pages.select_questions_for_pages(questions, pkg.n_pages)
    sibling = [(pages.page_slug(q, ci), f"Q{q.id}: {q.keyword}") for q in page_questions]
    pages_dir = out_dir / "pages"
    pages_dir.mkdir(exist_ok=True)
    pages_urls: list[str] = []
    for q in page_questions:
        resp = _pick_page_response(q, responses)
        html = pages.render_page(q, resp, ci, sibling, emit_schema=pkg.schema)
        slug = pages.page_slug(q, ci)
        (pages_dir / f"{slug}.html").write_text(html, encoding="utf-8")
        pages_urls.append(f"{ci.website.rstrip('/')}/{slug}.html")
    print(f"STEP 5  built {len(page_questions)} indexing pages (schema={pkg.schema}) -> pages/")

    # --- STEP 6: sitemap ----------------------------------------------------
    (out_dir / "sitemap.xml").write_text(pages.render_sitemap(pages_urls), encoding="utf-8")
    report.write_links(master, pages_urls, out_dir)
    print("STEP 6  sitemap.xml + indexing_urls.txt + source_links.csv")

    # --- STEP 7: deliverables (only with real captures) --------------------
    if has_responses:
        report.render_pdf_report(ci, master, src_freq, comp_freq, pages_urls, out_dir / "report.pdf")
        made, expected = report.write_screenshots(
            questions, responses, ci, out_dir / "screenshots"
        )
        report.write_submission_checklist(ci, pages_urls, out_dir)
        manifest = report.write_manifest(out_dir)
        archive = report.assemble_zip(out_dir)
        print(
            f"STEP 7  report.pdf + {made} screenshot(s) ({len(expected)} still manual) "
            f"+ checklist + manifest ({manifest['file_count']} files)"
        )
        print(f"        ZIP deliverable: {archive}")
    else:
        print(
            "STEP 7  skipped (no --responses). Pages/tables rendered with "
            "'[pending capture]'. Fill responses_template.csv, then re-run with "
            "--responses to produce the PDF, screenshots and ZIP."
        )

    print(f"\nDone. Output: {out_dir}")
    return out_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="engine",
        description="AI Mention - LLM Query Seeding engine.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="Run the service for one client input.")
    run_p.add_argument("--input", required=True, help="Path to client input JSON.")
    run_p.add_argument("--responses", default=None, help="Path to filled capture CSV (optional).")
    run_p.add_argument("--out", default="outputs", help="Output root directory (default: outputs).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        try:
            run(args.input, args.responses, args.out)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
