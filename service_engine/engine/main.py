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

from . import extractor, generator, ingest, pages, report, verify
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


def _order_ident(input_path: str, order_id: str | None):
    ci = ClientInput.from_json(input_path)
    slug = ci.client_slug or pages.slugify(ci.brand)
    oid = pages.slugify(order_id or ci.order_id or "order-001")
    inputs_root = Path(input_path).resolve().parent
    return ci, slug, oid, inputs_root


def ingest_only(input_path: str, responses_path: str, order_id: str | None, captures_dir: str | None) -> dict:
    ci, slug, oid, inputs_root = _order_ident(input_path, order_id)
    captures = captures_dir or (inputs_root / "captures" / slug / oid)
    questions = generator.generate_questions(ci, ci.pkg.n_questions)
    stats = ingest.ingest_captures(ci, questions, responses_path, captures)
    print(f"INGEST  from {captures}")
    print("        " + ", ".join(f"{m}: +{n}" for m, n in stats.items()))
    return stats


def deliver(input_path: str, responses_path: str, out_root: str, order_id: str | None,
            captures_dir: str | None = None, proof_ok_models: set[str] | None = None,
            require_evidence: set[str] | None = None) -> dict:
    """End-to-end: ingest dropped answers -> regenerate the whole package -> strict QA.
    The operator only supplies raw answers + screenshots; the engine does the rest."""
    ci, slug, oid, inputs_root = _order_ident(input_path, order_id)
    ingest_only(input_path, responses_path, order_id, captures_dir)
    print()
    run(input_path, responses_path, out_root, order_id)
    print()
    result = verify.verify_order(
        out_root, slug, oid, strict_screenshots=True,
        proof_ok_models=proof_ok_models or set(),
        screenshots_input=str(inputs_root / "screenshots" / slug / oid),
        require_evidence=require_evidence or set(),
    )
    print(verify.format_report(result))
    zip_path = Path(out_root) / slug / f"{oid}_deliverable.zip"
    print(f"\nZIP: {zip_path}")
    print("STATUS: " + ("COMPLETE (strict QA PASS)" if result["overall"] != verify.FAIL
                        else "NOT COMPLETE - strict QA did not pass (see [FAIL] above)"))
    return result


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
    verify_p.add_argument("--proof-ok-models", dest="proof_ok_models", default="",
                          help="Comma list of models allowed to use an engine proof card instead of a "
                          "real browser screenshot (e.g. 'Claude'). Only affects --strict-screenshots.")
    verify_p.add_argument("--screenshots-input", dest="screenshots_input", default=None,
                          help="Persistent real-screenshots input dir (default: inputs/screenshots/<slug>/<order>).")
    verify_p.add_argument("--require-evidence", dest="require_evidence", default="",
                          help="Comma list of models that MUST be real captures (evidence browser/operator), "
                          "e.g. 'ChatGPT,Gemini,Perplexity'. Fails proof/api/none for those models.")

    ingest_p = sub.add_parser("ingest", help="Merge dropped per-model answer files into the responses CSV.")
    ingest_p.add_argument("--input", required=True, help="Path to client input JSON.")
    ingest_p.add_argument("--responses", required=True, help="Responses CSV to update (created if absent).")
    ingest_p.add_argument("--order-id", dest="order_id", default=None, help="Order id.")
    ingest_p.add_argument("--captures", default=None,
                          help="Drop-folder (default: inputs/captures/<slug>/<order>).")

    deliver_p = sub.add_parser(
        "deliver", help="End-to-end: ingest dropped answers -> regenerate package -> strict QA.")
    deliver_p.add_argument("--input", required=True, help="Path to client input JSON.")
    deliver_p.add_argument("--responses", required=True, help="Responses CSV (updated by ingest).")
    deliver_p.add_argument("--order-id", dest="order_id", default=None, help="Order id.")
    deliver_p.add_argument("--out", default="outputs", help="Output root directory (default: outputs).")
    deliver_p.add_argument("--captures", default=None,
                           help="Drop-folder (default: inputs/captures/<slug>/<order>).")
    deliver_p.add_argument("--proof-ok-models", dest="proof_ok_models", default="",
                           help="Models allowed to use an engine proof card (e.g. 'Claude').")
    deliver_p.add_argument("--require-evidence", dest="require_evidence", default="",
                           help="Models that MUST be real captures (evidence browser/operator).")

    capture_p = sub.add_parser(
        "capture", help="Real browser capture (Playwright, human-in-the-loop). Operator environment.")
    capture_p.add_argument("--input", required=True, help="Path to client input JSON.")
    capture_p.add_argument("--order-id", dest="order_id", default=None, help="Order id.")
    capture_p.add_argument("--models", default="", help="Comma list, e.g. chatgpt,gemini,perplexity.")
    capture_p.add_argument("--captures", default=None, help="Drop-folder (default inputs/captures/<slug>/<order>).")
    capture_p.add_argument("--shots", default=None, help="Screenshots dir (default inputs/screenshots/<slug>/<order>).")
    capture_p.add_argument("--questions", default=None, help="Question range, e.g. 1-25 (default: all).")
    capture_p.add_argument("--headful", action="store_true", help="Show the browser window (recommended).")
    capture_p.add_argument("--login-wait", dest="login_wait", action="store_true",
                           help="Pause for manual login on first navigation to each model.")
    capture_p.add_argument("--resume", action="store_true", help="Skip questions already captured.")
    capture_p.add_argument("--prepare-only", dest="prepare_only", action="store_true",
                           help="Only write per-question prompt files (no browser).")
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
        proof_ok = {m.strip() for m in (args.proof_ok_models or "").split(",") if m.strip()}
        require_ev = {m.strip() for m in (args.require_evidence or "").split(",") if m.strip()}
        result = verify.verify_order(
            args.out, args.client_slug, args.order_id,
            min_intake=args.min_intake, strict_screenshots=args.strict_screenshots,
            proof_ok_models=proof_ok, screenshots_input=args.screenshots_input,
            require_evidence=require_ev,
        )
        print(verify.format_report(result))
        return 1 if result["overall"] == verify.FAIL else 0
    elif args.command == "ingest":
        try:
            ingest_only(args.input, args.responses, args.order_id, args.captures)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    elif args.command == "deliver":
        try:
            proof_ok = {m.strip() for m in (args.proof_ok_models or "").split(",") if m.strip()}
            require_ev = {m.strip() for m in (args.require_evidence or "").split(",") if m.strip()}
            result = deliver(args.input, args.responses, args.out, args.order_id,
                             captures_dir=args.captures, proof_ok_models=proof_ok,
                             require_evidence=require_ev)
            return 1 if result["overall"] == verify.FAIL else 0
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    elif args.command == "capture":
        from .capture.runner import run_capture  # lazy: avoids importing playwright unless used
        try:
            models = [m.strip() for m in (args.models or "").split(",") if m.strip()]
            return run_capture(
                input_path=args.input, order_id=args.order_id, models=models,
                captures_dir=args.captures, shots_dir=args.shots, questions_range=args.questions,
                headful=args.headful, login_wait=args.login_wait, resume=args.resume,
                prepare_only=args.prepare_only,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
