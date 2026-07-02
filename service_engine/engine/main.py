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

from . import extractor, generator, pages, report, verify
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


def run(input_path: str, responses_path: str | None, out_root: str, order_id: str | None = None) -> Path:
    ci = ClientInput.from_json(input_path)

    # Resolve client/order identity. Each order is isolated in its own folder so
    # re-running one order never overwrites another, and client data cannot mix.
    client_slug = ci.client_slug or pages.slugify(ci.brand)
    order_id = order_id or ci.order_id
    if not order_id:
        order_id = "order-001"
        ci.warnings.append(
            "no --order-id (and no 'order_id' in input) - defaulting to 'order-001'. "
            "Pass a unique order id per order (e.g. the SEOeStore order number)."
        )
    order_id = pages.slugify(order_id)
    # Write the resolved identity back so brief/manifest reflect the actual run.
    ci.order_id = order_id
    ci.client_slug = client_slug

    for w in ci.warnings:
        print(f"  ! warning: {w}")

    pkg = ci.pkg
    out_dir = Path(out_root) / client_slug / order_id
    if out_dir.exists():
        shutil.rmtree(out_dir)  # only THIS order's folder; other orders untouched
    out_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Client: {ci.brand}  |  Slug: {client_slug}  |  Order: {order_id}  |  "
        f"Package: {pkg.name}  |  Models: {', '.join(pkg.models)}"
    )

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

    # Sanity check: guard against pointing at the wrong responses file (data mixing).
    if has_responses:
        gen_ids = {q.id for q in questions}
        resp_ids = {r.question_id for r in responses}
        if resp_ids != gen_ids:
            print(
                "  ! warning: responses question_ids do not match generated questions "
                f"(missing={sorted(gen_ids - resp_ids)}, extra={sorted(resp_ids - gen_ids)}). "
                "Confirm this responses file belongs to THIS order."
            )

    # --- STEP 4: master table & frequencies --------------------------------
    master = extractor.build_master_table(questions, responses, ci)
    src_freq = extractor.source_frequency(responses)
    comp_freq = extractor.competitor_frequency(responses)
    report.write_tables(master, src_freq, comp_freq, out_dir)
    print(f"STEP 4  master_table.csv ({len(master)} rows) + frequency tables")

    # --- STEP 5: crawlable support pages -----------------------------------
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
    print(f"STEP 5  built {len(page_questions)} crawlable support pages (schema={pkg.schema}) -> pages/")

    # --- STEP 6: sitemap (publish & make crawlable) ------------------------
    (out_dir / "sitemap.xml").write_text(pages.render_sitemap(pages_urls), encoding="utf-8")
    report.write_links(master, pages_urls, out_dir)
    print("STEP 6  sitemap.xml + support_page_urls.txt + source_links.csv")

    # Order brief (intake echo + safety constraints) - always written.
    report.write_order_brief(ci, input_path, responses_path, out_dir)

    order_meta = {
        "brand": ci.brand,
        "client_slug": client_slug,
        "order_id": order_id,
        "package": ci.package,
        "models": list(pkg.models),
        "report_date": report.REPORT_DATE,
    }

    # Persistent location for operator-supplied real full-page screenshots. Lives
    # next to the inputs (not under out_dir, which is wiped each run), so real
    # screenshots survive re-runs and are copied into the delivered screenshots/.
    shots_input = Path(input_path).resolve().parent / "screenshots" / client_slug / order_id

    # --- STEP 7: deliverables (only with real captures) --------------------
    if has_responses:
        report.render_pdf_report(ci, master, src_freq, comp_freq, pages_urls, out_dir / "report.pdf")
        made, expected = report.write_screenshots(
            questions, responses, ci, out_dir / "screenshots", provided_dir=shots_input
        )
        report.write_submission_checklist(ci, pages_urls, out_dir)
        manifest = report.write_manifest(out_dir, order_meta)
        archive_base = Path(out_root) / client_slug / f"{order_id}_deliverable"
        archive = report.assemble_zip(out_dir, archive_base)
        print(
            f"STEP 7  report.pdf + {made} screenshot(s) assembled ({len(expected)} manual screenshots pending) "
            f"+ checklist + order_brief + manifest ({manifest['file_count']} files)"
        )
        print(f"        ZIP deliverable: {archive}")
    else:
        report.write_manifest(out_dir, order_meta)
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
        description="AI Mention - AI visibility baseline & LLM query testing engine.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="Run the service for one client order.")
    run_p.add_argument("--input", required=True, help="Path to client input JSON.")
    run_p.add_argument("--responses", default=None, help="Path to filled capture CSV (optional).")
    run_p.add_argument("--out", default="outputs", help="Output root directory (default: outputs).")
    run_p.add_argument(
        "--order-id",
        dest="order_id",
        default=None,
        help="Unique order id (e.g. SEOeStore order number). Falls back to 'order_id' in the "
        "input JSON, else 'order-001'. Output goes to outputs/<client-slug>/<order-id>/.",
    )

    verify_p = sub.add_parser("verify", help="QA gate: check an order folder before delivery.")
    verify_p.add_argument("--client-slug", dest="client_slug", required=True, help="Client slug.")
    verify_p.add_argument("--order-id", dest="order_id", required=True, help="Order id.")
    verify_p.add_argument("--out", default="outputs", help="Output root directory (default: outputs).")
    verify_p.add_argument("--min-intake", dest="min_intake", type=int, default=8,
                          help="Minimum acceptable intake completeness (default: 8).")
    verify_p.add_argument("--strict-screenshots", dest="strict_screenshots", action="store_true",
                          help="Treat missing manual full-page screenshots as a FAIL (not a WARN).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        try:
            run(args.input, args.responses, args.out, args.order_id)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    elif args.command == "verify":
        result = verify.verify_order(
            args.out, args.client_slug, args.order_id,
            min_intake=args.min_intake, strict_screenshots=args.strict_screenshots,
        )
        print(verify.format_report(result))
        return 1 if result["overall"] == verify.FAIL else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
