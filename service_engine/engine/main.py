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

from . import dir_ai, extractor, generator, ingest, pages, report, verify
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


def _collect_delivery(input_path: str, order_id: str | None, models_arg: str,
                      questions_arg: str | None):
    """Gather the real browser captures for a scoped delivery (shared by publish/deliver)."""
    from . import delivery
    from .capture.runner import _parse_range

    ci, slug, oid, inputs_root = _order_ident(input_path, order_id)
    questions = generator.generate_questions(ci, ci.pkg.n_questions)
    qids = set(_parse_range(questions_arg, len(questions)))
    selected = [q for q in questions if q.id in qids]
    models = [m.strip().lower() for m in (models_arg or "").split(",") if m.strip()] \
        or ["chatgpt", "gemini"]
    d = delivery.collect(
        captures_dir=inputs_root / "captures" / slug / oid,
        shots_dir=inputs_root / "screenshots" / slug / oid,
        questions=selected, models=models, brand=ci.brand, website=ci.website,
        order_id=oid, client_slug=slug,
    )
    d.blocked = {
        "claude": {"blocker": "Cloudflare bot verification (does not self-clear)"},
        "perplexity": {"blocker": "Cloudflare bot verification (does not self-clear)"},
    }
    return ci, slug, oid, d


def _load_image_urls(order_dir: Path) -> dict[tuple[str, str], str]:
    """(query_id, model) -> public screenshot URL, from screenshot_urls.csv if present."""
    import csv as _csv
    p = Path(order_dir) / "screenshot_urls.csv"
    if not p.exists():
        return {}
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return {(r["query_id"], r["model"]): r["public_image_url"]
                for r in _csv.DictReader(fh) if r.get("public_image_url")}


def _publish_rows(d, safe_only: bool) -> list[dict]:
    caps = d.safe if safe_only else d.captures
    return [{
        "query_id": f"q{c.question_id}", "model": c.model_label, "public_url": "",
        "safe_to_share": "yes" if c.safe else "no",
        "screenshot_path": c.screenshot_path.as_posix(),
        "answer_path": c.answer_path.as_posix(),
    } for c in caps]


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
    deliver_p.add_argument("--scope", default=None,
                           help="Declare a partial delivery, e.g. 'two-model' (ChatGPT+Gemini "
                                "browser-captured). Builds the internal + client-safe reports "
                                "and the scoped ZIP instead of the full 4-model package.")
    deliver_p.add_argument("--models", default="", help="Models in scope (default: chatgpt,gemini).")
    deliver_p.add_argument("--questions", default=None, help="Question range in scope, e.g. 1-10.")

    capture_p = sub.add_parser(
        "capture", help="Real browser capture (Playwright, human-in-the-loop). Operator environment.")
    capture_p.add_argument("--input", required=True, help="Path to client input JSON.")
    capture_p.add_argument("--order-id", dest="order_id", default=None, help="Order id.")
    capture_p.add_argument("--models", default="", help="Comma list, e.g. chatgpt,gemini,perplexity.")
    capture_p.add_argument("--captures", default=None, help="Drop-folder (default inputs/captures/<slug>/<order>).")
    capture_p.add_argument("--shots", default=None, help="Screenshots dir (default inputs/screenshots/<slug>/<order>).")
    capture_p.add_argument("--questions", default=None, help="Question range, e.g. 1-25 (default: all).")
    capture_p.add_argument("--headless", action="store_true",
                           help="Hide the browser window (default: visible, recommended).")
    capture_p.add_argument("--login-wait", dest="login_wait", action="store_true",
                           help="Pause for manual sign-in before capturing.")
    capture_p.add_argument("--smoke", action="store_true",
                           help="Smoke test: exactly 1 model x 1 question, to prove the flow.")
    capture_p.add_argument("--confirm-each", dest="confirm_each", action="store_true",
                           help="Pause for operator confirmation before each screenshot.")
    capture_p.add_argument("--timeout", type=int, default=180,
                           help="Seconds to wait for one answer to finish (default: 180).")
    capture_p.add_argument("--resume", action="store_true", help="Skip questions already captured.")
    capture_p.add_argument("--prepare-only", dest="prepare_only", action="store_true",
                           help="Only write per-question prompt files (no browser).")
    capture_p.add_argument("--connect-cdp", dest="connect_cdp", default=None,
                           help="Attach to a Chrome YOU started (e.g. http://127.0.0.1:9222) "
                                "instead of launching one. Use this when the operator has "
                                "already signed in and cleared Cloudflare/MFA by hand.")

    login_p = sub.add_parser(
        "login", help="Open Chrome with the persistent profile so the operator can sign in.")
    login_p.add_argument("--model", required=True, help="chatgpt | gemini | claude | perplexity")
    login_p.add_argument("--headless", action="store_true", help="(not recommended - login needs the UI)")
    login_p.add_argument("--connect-cdp", dest="connect_cdp", default=None,
                         help="Verify access in a Chrome YOU started, e.g. http://127.0.0.1:9222")

    cs_p = sub.add_parser(
        "chrome-start", help="Print (or run) the exact Chrome command for CDP attach mode.")
    cs_p.add_argument("--model", default="all",
                      help="chatgpt | gemini | claude | perplexity | all (default: all).")
    cs_p.add_argument("--profile", default=None,
                      help="Profile name (default: 'shared' for --model all, else the model). "
                           "One shared profile = one Chrome, one login session for every model.")
    cs_p.add_argument("--port", type=int, default=9222, help="Remote debugging port (default 9222).")
    cs_p.add_argument("--run", action="store_true", help="Actually start Chrome now.")

    ss_p = sub.add_parser(
        "session-status",
        help="Check, per model, whether the attached Chrome is signed in and capture-ready.")
    ss_p.add_argument("--connect-cdp", dest="connect_cdp", default="http://127.0.0.1:9222",
                      help="CDP endpoint of the Chrome you started (default http://127.0.0.1:9222).")
    ss_p.add_argument("--models", default="chatgpt,gemini,claude,perplexity",
                      help="Comma list to check.")

    cqa_p = sub.add_parser(
        "capture-qa", help="Strict QA on real browser evidence (answer + provenance + screenshot).")
    cqa_p.add_argument("--input", required=True, help="Path to client input JSON.")
    cqa_p.add_argument("--order-id", dest="order_id", default=None, help="Order id.")
    cqa_p.add_argument("--model", required=True, help="Model to verify, e.g. chatgpt.")
    cqa_p.add_argument("--questions", default=None, help="Question range, e.g. 1 or 1-25 (default: all).")
    cqa_p.add_argument("--captures", default=None, help="Drop-folder (default inputs/captures/<slug>/<order>).")
    cqa_p.add_argument("--shots", default=None, help="Screenshots dir (default inputs/screenshots/<slug>/<order>).")

    up_p = sub.add_parser(
        "screenshots-upload",
        help="Upload client-safe proof screenshots to S3-compatible storage and record URLs.")
    up_p.add_argument("--input", required=True, help="Path to client input JSON.")
    up_p.add_argument("--order-id", dest="order_id", default=None, help="Order id.")
    up_p.add_argument("--models", default="chatgpt,gemini", help="Comma list.")
    up_p.add_argument("--questions", default=None, help="Question range, e.g. 1-10.")
    up_p.add_argument("--out", default="outputs", help="Output root (default: outputs).")
    up_p.add_argument("--prefix", default=None, help="Object key prefix (default: ai-mention).")
    up_p.add_argument("--safe-only", dest="safe_only", action="store_true", default=True,
                      help="Upload only client-safe captures (default, and enforced).")
    up_p.add_argument("--dry-run", dest="dry_run", action="store_true",
                      help="Show keys/URLs without uploading.")
    up_p.add_argument("--show-config", dest="show_config", action="store_true",
                      help="Print the storage config with secrets masked, then exit.")

    rev_p = sub.add_parser(
        "review", help="Sentiment/risk screen of captured answers (run before any client report).")
    rev_p.add_argument("--input", required=True, help="Path to client input JSON.")
    rev_p.add_argument("--order-id", dest="order_id", default=None, help="Order id.")
    rev_p.add_argument("--models", default="", help="Comma list (default: package models).")
    rev_p.add_argument("--questions", default=None, help="Question range, e.g. 1-10 (default: all).")
    rev_p.add_argument("--captures", default=None, help="Drop-folder (default inputs/captures/<slug>/<order>).")
    rev_p.add_argument("--shots", default=None, help="Screenshots dir (default inputs/screenshots/<slug>/<order>).")
    rev_p.add_argument("--out", default=None, help="Write the review CSV + markdown table here.")

    qs_p = sub.add_parser("questions", help="Print the generated question set (no capture).")
    qs_p.add_argument("--input", required=True, help="Path to client input JSON.")
    qs_p.add_argument("--query-mode", dest="query_mode", default=None,
                      help="benefit (feature-led, default) | audit (evaluative reputation set).")
    qs_p.add_argument("--limit", type=int, default=0, help="Show only the first N questions.")

    prep_p = sub.add_parser(
        "publish-prepare", help="Build publish payloads / publish-ready folder (no credentials needed).")
    prep_p.add_argument("--input", default=None, help="Client input JSON (Directory Article API mode).")
    prep_p.add_argument("--client-slug", dest="client_slug", default=None, help="Client slug (static-site mode).")
    prep_p.add_argument("--order-id", dest="order_id", required=True, help="Order id.")
    prep_p.add_argument("--models", default="", help="Comma list, e.g. chatgpt,gemini.")
    prep_p.add_argument("--questions", default=None, help="Question range, e.g. 1-10 (default: all).")
    prep_p.add_argument("--safe-only", dest="safe_only", action="store_true",
                        help="Only include captures the risk review marked client-safe.")
    prep_p.add_argument("--out", default="outputs", help="Output root directory (default: outputs).")
    prep_p.add_argument("--public-base-url", dest="public_base_url", default="",
                        help="Public URL the remote root maps to (static-site mode).")
    prep_p.add_argument("--no-screenshots", dest="no_screenshots", action="store_true",
                        help="Do not include proof screenshots in the upload set.")

    pub_p = sub.add_parser("publish", help="Publish pages via the Directory Article API (or a configured site).")
    pub_p.add_argument("--input", default=None, help="Client input JSON (Directory Article API mode).")
    pub_p.add_argument("--client-slug", dest="client_slug", default=None, help="Client slug (static-site mode).")
    pub_p.add_argument("--order-id", dest="order_id", required=True, help="Order id.")
    pub_p.add_argument("--models", default="", help="Comma list, e.g. chatgpt,gemini.")
    pub_p.add_argument("--questions", default=None, help="Question range, e.g. 1-10 (default: all).")
    pub_p.add_argument("--safe-only", dest="safe_only", action="store_true",
                       help="Only publish captures the risk review marked client-safe.")
    pub_p.add_argument("--api-endpoint", dest="api_endpoint", default=dir_ai.API_ENDPOINT,
                       help=f"Directory Article API endpoint (default: {dir_ai.API_ENDPOINT}).")
    pub_p.add_argument("--out", default="outputs", help="Output root directory (default: outputs).")
    pub_p.add_argument("--config", default=None, help="Static-site publish config JSON (static-site mode).")
    pub_p.add_argument("--dry-run", dest="dry_run", action="store_true",
                       help="Show exactly what would be published without sending anything.")
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
    elif args.command == "deliver" and args.scope:
        # Scoped delivery: build the internal + client-safe reports and ZIP from the
        # real browser captures for the declared models only.
        from . import delivery
        from .capture import qa as capture_qa
        try:
            ci, slug, oid, d = _collect_delivery(args.input, args.order_id, args.models, args.questions)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        if not d.captures:
            print("ERROR: no real browser captures found for the requested scope. "
                  "Nothing was generated (results are never fabricated).", file=sys.stderr)
            return 1

        qa_lines = [f"Scope: {args.scope}", f"Order: {oid}", ""]
        from .capture.runner import _parse_range
        questions = generator.generate_questions(ci, ci.pkg.n_questions)
        qids = _parse_range(args.questions, len(questions))
        inputs_root = Path(args.input).resolve().parent
        for model in sorted({c.model for c in d.captures}):
            res = capture_qa.verify_capture(
                inputs_root / "captures" / slug / oid,
                inputs_root / "screenshots" / slug / oid,
                model, qids, {q.id: q.text for q in questions})
            qa_lines.append(capture_qa.format_report(res))
            qa_lines.append("")
        for b in delivery.BLOCKED_MODELS:
            qa_lines.append(f"{b}: BLOCKED - no captures, excluded from this delivery.")

        published = []
        csv_path = Path(args.out) / slug / oid / "published_urls.csv"
        if csv_path.exists():
            import csv as _csv
            with csv_path.open(encoding="utf-8-sig", newline="") as fh:
                published = list(_csv.DictReader(fh))

        out_dir = Path(args.out) / slug / f"{oid}_two-model"
        result = delivery.assemble(d, out_dir, report.REPORT_DATE, published,
                                   "\n".join(qa_lines), published_csv=csv_path)
        print(f"{delivery.SCOPE_LABEL}")
        print(f"  captures included : {len(d.captures)} (safe={result['safe']}, "
              f"excluded={result['excluded']})")
        print(f"  internal report   : {result['internal_report']}")
        print(f"  client report     : {result['client_report']}")
        print(f"  ZIP               : {result['zip']}")
        print(f"  blocked           : {', '.join(delivery.BLOCKED_MODELS)} (excluded, not fabricated)")
        print("\nSTATUS: 2-model browser-captured delivery. NOT a full 4-model PRO delivery.")
        return 0
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
                headful=not args.headless, login_wait=args.login_wait, resume=args.resume,
                prepare_only=args.prepare_only, smoke=args.smoke,
                confirm_each=args.confirm_each, answer_timeout_s=args.timeout,
                cdp_endpoint=args.connect_cdp,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    elif args.command == "login":
        try:
            from .capture.session import open_login  # lazy: needs playwright
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: Playwright is not available ({exc}).", file=sys.stderr)
            print("  python -m pip install -r requirements-capture.txt", file=sys.stderr)
            print("  python -m playwright install chromium", file=sys.stderr)
            return 1
        try:
            return open_login(args.model, headful=not args.headless,
                              cdp_endpoint=args.connect_cdp)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    elif args.command == "chrome-start":
        from .capture.session import chrome_command, cdp_is_up, cdp_profile_dir
        profile = args.profile or ("shared" if args.model == "all" else args.model)
        cmd = chrome_command(profile, args.port)
        endpoint = f"http://127.0.0.1:{args.port}"
        print(f"Profile : {cdp_profile_dir(profile)}")
        print(f"Endpoint: {endpoint}")
        print("\nStart Chrome with:")
        print(f"  {cmd}\n")
        if args.run:
            import subprocess
            subprocess.Popen(cmd, shell=True)
            print("Chrome starting...")
        already = cdp_is_up(endpoint)
        if already:
            print(f"Already listening: {already.get('Browser', '?')}")
        print("Then, in that window: sign in to each model and clear any "
              "Cloudflare/MFA check by hand.")
        print("\nVerify every model is signed in:")
        print(f"  python -m engine.main session-status --connect-cdp {endpoint}")
        print("Capture (per model, 25 questions):")
        one = "chatgpt" if args.model == "all" else args.model
        print(f"  python -m engine.main capture --input inputs/1billionlinks.json "
              f"--order-id 2026-06-28-001 --models {one} --questions 1-25 "
              f"--connect-cdp {endpoint} --resume")
        return 0
    elif args.command == "session-status":
        from .capture.session import session_status
        models = [m.strip().lower() for m in (args.models or "").split(",") if m.strip()]
        try:
            rows = session_status(args.connect_cdp, models)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"Chrome: {args.connect_cdp}\n")
        not_ready = []
        for r in rows:
            mark = ("READY" if r["ready"]
                    else "SIGN IN NEEDED" if r["reachable"] else "NOT REACHABLE")
            if not r["ready"]:
                not_ready.append(r["model"])
            print(f"  {r['model']:11} {mark:16} {r['detail']}")
        print()
        if not not_ready:
            print("All requested models are signed in and capture-ready.")
            return 0
        print(f"Sign in to {', '.join(not_ready)} IN THAT CHROME WINDOW, then re-run this.")
        return 1
    elif args.command == "capture-qa":
        from .capture import qa as capture_qa
        from .capture.runner import _parse_range
        try:
            ci, slug, oid, inputs_root = _order_ident(args.input, args.order_id)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        questions = generator.generate_questions(ci, ci.pkg.n_questions)
        qids = _parse_range(args.questions, len(questions))
        caps = args.captures or (inputs_root / "captures" / slug / oid)
        shots = args.shots or (inputs_root / "screenshots" / slug / oid)
        result = capture_qa.verify_capture(
            caps, shots, args.model, qids, {q.id: q.text for q in questions})
        print(capture_qa.format_report(result))
        return 1 if result["overall"] == capture_qa.FAIL else 0
    elif args.command == "questions":
        try:
            ci = ClientInput.from_json(args.input)
            mode = generator.resolve_mode(ci, args.query_mode)
            qs = generator.generate_questions(ci, ci.pkg.n_questions, mode=mode)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        shown = qs[: args.limit] if args.limit else qs
        print(f"Query mode: {mode}  |  {len(qs)} questions  |  showing {len(shown)}\n")
        for q in shown:
            print(f"Q{q.id:<3} [{q.category} / {q.keyword}]\n     {q.text}")
        hits = generator.lint_questions(shown)
        print()
        if hits:
            print(f"RISK LINT: {len(hits)} risky prompt(s) found:")
            for qid, phrase, text in hits:
                print(f"  Q{qid}: matched {phrase!r}")
            return 1
        print("RISK LINT: clean - no judgment/trust/competitor phrasing.")
        return 0
    elif args.command == "screenshots-upload":
        from . import s3_upload
        if args.show_config:
            try:
                for k, v in s3_upload.safe_config_summary().items():
                    print(f"  {k:16} = {v}")
            except (FileNotFoundError, ValueError) as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
            return 0
        try:
            ci, slug, oid, d = _collect_delivery(args.input, args.order_id, args.models, args.questions)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        # Unsafe captures are never uploaded: a public asset cannot be un-published.
        items = [{"query_id": f"q{c.question_id}", "model": c.model_label,
                  "screenshot_path": str(c.screenshot_path),
                  "safe_to_share": "yes" if c.safe else "no"}
                 for c in d.captures]
        try:
            rows = s3_upload.upload_screenshots(
                items, slug, oid, prefix=args.prefix or s3_upload.AIMENTION_PREFIX,
                dry_run=args.dry_run)
        except (FileNotFoundError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        csv_path = s3_upload.write_upload_csv(
            rows, Path(args.out) / slug / oid / "screenshot_urls.csv")
        uploaded = [r for r in rows if r["public_image_url"] and "FAILED" not in r["uploaded_at"]]
        skipped = [r for r in rows if "SKIPPED" in r["uploaded_at"]]
        failed = [r for r in rows if "FAILED" in r["uploaded_at"]]
        print(f"uploaded={len(uploaded)}  skipped_unsafe={len(skipped)}  failed={len(failed)}")
        for r in skipped:
            print(f"  skipped (unsafe, not public): {r['query_id']}/{r['model']}")
        for r in failed:
            print(f"  FAILED {r['query_id']}/{r['model']}: {r['uploaded_at']}")
        if uploaded and not args.dry_run:
            print("\nverifying public reachability...")
            bad = []
            for r in uploaded:
                ok, detail = s3_upload.verify_public(r["public_image_url"])
                if not ok:
                    bad.append((r["query_id"], r["model"], detail))
            print(f"  publicly reachable: {len(uploaded) - len(bad)}/{len(uploaded)}")
            for q, m, det in bad:
                print(f"  NOT REACHABLE {q}/{m}: {det}")
        print(f"\nURL map: {csv_path}")
        return 1 if failed else 0
    elif args.command == "review":
        from . import sentiment
        from .capture.runner import _parse_range
        try:
            ci, slug, oid, inputs_root = _order_ident(args.input, args.order_id)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        questions = generator.generate_questions(ci, ci.pkg.n_questions)
        qids = set(_parse_range(args.questions, len(questions)))
        selected = [q for q in questions if q.id in qids]
        models = [m.strip() for m in (args.models or "").split(",") if m.strip()] or list(ci.pkg.models)
        caps = args.captures or (inputs_root / "captures" / slug / oid)
        shots = args.shots or (inputs_root / "screenshots" / slug / oid)

        rows = sentiment.review_order(caps, shots, models, selected, brand=ci.brand)
        if not rows:
            print(f"No captured answers found under {caps} for models {models}.")
            return 1
        print(sentiment.format_table(rows))
        print()
        for model, s in sentiment.summarize(rows).items():
            print(f"  {model:12} total={s['total']:3}  positive={s[sentiment.POSITIVE]:3} "
                  f"neutral={s[sentiment.NEUTRAL]:3}  negative={s[sentiment.NEGATIVE]:3} "
                  f"unsafe={s[sentiment.UNSAFE]:3}"
                  + (f"  flagged: {s['unsafe_ids']}" if s["unsafe_ids"] else ""))
        if args.out:
            sentiment.write_review_csv(rows, Path(args.out) / "sentiment_review.csv")
            (Path(args.out) / "sentiment_review.md").write_text(
                sentiment.format_table(rows) + "\n", encoding="utf-8")
            print(f"\nWritten: {Path(args.out) / 'sentiment_review.csv'} + .md")
        return 1 if any(r["safe"] == "No" for r in rows) else 0
    elif args.command == "publish-prepare" and args.input:
        # Directory Article API mode: build one inline-JSON payload per capture.
        try:
            ci, slug, oid, d = _collect_delivery(args.input, args.order_id, args.models, args.questions)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        caps = d.safe if args.safe_only else d.captures
        image_urls = _load_image_urls(Path(args.out) / slug / oid)
        pub_dir = Path(args.out) / slug / oid / "publish"
        (pub_dir / "payloads").mkdir(parents=True, exist_ok=True)
        for c in caps:
            payload = dir_ai.build_payload(
                brand=ci.brand, website=ci.website, model=c.model, question_id=c.question_id,
                query=c.query, answer=c.answer, order_id=oid, evidence_type=c.evidence_type,
                screenshot_path=c.screenshot_path.as_posix(),
                capture_time=c.provenance.get("captured_at", ""), client_safe=c.safe,
                keyword=c.keyword,
                image_url=image_urls.get((f"q{c.question_id}", c.model_label), ""),
            )
            (pub_dir / "payloads" / f"q{c.question_id}_{c.model}.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        # Also stage the by-name bundle: {name}/{name}.txt + {name}/{name}.png, exactly
        # as the API guide's Option 1 expects. That route is the only documented one
        # that renders a screenshot on the page.
        byname_root = pub_dir / "by-name"
        names: list[tuple[str, object]] = []
        for c in caps:
            name = dir_ai.content_name(slug, c.question_id, c.model)
            ndir = byname_root / name
            ndir.mkdir(parents=True, exist_ok=True)
            payload = dir_ai.build_payload(
                brand=ci.brand, website=ci.website, model=c.model, question_id=c.question_id,
                query=c.query, answer=c.answer, order_id=oid, evidence_type=c.evidence_type,
                screenshot_path=c.screenshot_path.as_posix(),
                capture_time=c.provenance.get("captured_at", ""), client_safe=c.safe,
                keyword=c.keyword,
                image_url=image_urls.get((f"q{c.question_id}", c.model_label), ""),
            )
            (ndir / f"{name}.txt").write_text(
                dir_ai.build_txt_file(payload, name, c.provenance.get("captured_at", "")),
                encoding="utf-8")
            shutil.copyfile(c.screenshot_path, ndir / f"{name}.png")
            names.append((name, c))

        (pub_dir / "SCREENSHOT_HOSTING.md").write_text(
            "# Screenshots: what is ready and what is still needed\n\n"
            "This engine does NOT claim to upload images and never invents a public image URL.\n\n"
            "## Ready now: the by-name bundle\n\n"
            f"`by-name/` holds {len(names)} folders, each already in the exact shape the API "
            "guide's Option 1 expects:\n\n"
            "```\nby-name/<name>/<name>.txt   documented plain-text content format\n"
            "by-name/<name>/<name>.png   the real full-page screenshot\n```\n\n"
            "Upload each folder to the data folder so the files resolve at:\n\n"
            "```\nhttps://myqsd.com/dir-ai-data/<name>/<name>.txt\n"
            "https://myqsd.com/dir-ai-data/<name>/<name>.png\n```\n\n"
            "Then publish each one with `{\"name\": \"<name>\"}` and the page renders WITH its "
            "screenshot, and stays live-linked (editing the .txt updates the page).\n\n"
            "## What is still missing\n\n"
            "The API guide documents how to *reference* files in the data folder but not how to "
            "*upload* to it. We need one of:\n\n"
            "1. the upload route / credentials for `dir-ai-data/` (SFTP, S3 bucket, admin UI), or\n"
            "2. any public HTTPS host for these files - the `file` route accepts an allowed-host "
            "URL, and `image` accepts an absolute URL.\n\n"
            "## Names prepared\n\n"
            + "\n".join(f"- `{n}` — {c.model_label} Q{c.question_id}" for n, c in names)
            + "\n\nUntil upload happens, inline-JSON publishing works but the page carries no "
              "screenshot; screenshots ship in the delivery ZIP instead.\n",
            encoding="utf-8")
        print(f"Prepared {len(caps)} payload(s) -> {pub_dir / 'payloads'}")
        print(f"  safe-only: {args.safe_only}  |  safe={len(d.safe)}  excluded={len(d.unsafe)}")
        print(f"  by-name bundles ({len(names)}, .txt + .png, NOT uploaded): {byname_root}")
        print(f"  hosting requirements: {pub_dir / 'SCREENSHOT_HOSTING.md'}")
        print(f"\nPublish with:\n  set {dir_ai.API_KEY_ENV}=... (or export)\n"
              f"  python -m engine.main publish --input {args.input} --order-id {oid} "
              f"--models {args.models or 'chatgpt,gemini'}"
              f"{' --safe-only' if args.safe_only else ''}")
        return 0
    elif args.command == "publish" and args.input:
        try:
            ci, slug, oid, d = _collect_delivery(args.input, args.order_id, args.models, args.questions)
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        caps = d.safe if args.safe_only else d.captures
        order_dir = Path(args.out) / slug / oid
        image_urls = _load_image_urls(order_dir)
        rows, failures = [], []
        key_present = dir_ai.api_key() is not None
        if not key_present and not args.dry_run:
            print(f"ERROR: {dir_ai.API_KEY_ENV} is not set. Nothing was published.", file=sys.stderr)
            print(f"  Set it, then re-run:\n"
                  f"    $env:{dir_ai.API_KEY_ENV}='<key>'   # PowerShell\n"
                  f"    export {dir_ai.API_KEY_ENV}='<key>' # bash\n", file=sys.stderr)

        for c in caps:
            payload = dir_ai.build_payload(
                brand=ci.brand, website=ci.website, model=c.model, question_id=c.question_id,
                query=c.query, answer=c.answer, order_id=oid, evidence_type=c.evidence_type,
                screenshot_path=c.screenshot_path.as_posix(),
                capture_time=c.provenance.get("captured_at", ""), client_safe=c.safe,
                keyword=c.keyword,
                image_url=image_urls.get((f"q{c.question_id}", c.model_label), ""),
            )
            row = {"query_id": f"q{c.question_id}", "model": c.model_label, "public_url": "",
                   "safe_to_share": "yes" if c.safe else "no",
                   "screenshot_path": c.screenshot_path.as_posix(),
                   "answer_path": c.answer_path.as_posix()}
            if args.dry_run:
                print(f"  DRY RUN q{c.question_id}/{c.model}: would POST "
                      f"{len(json.dumps(payload))} bytes to {args.api_endpoint}")
            elif not key_present:
                failures.append((f"q{c.question_id}/{c.model}", 0,
                                 f"{dir_ai.API_KEY_ENV} not set"))
            else:
                res = dir_ai.post_article(payload, endpoint=args.api_endpoint)
                if res["ok"]:
                    row["public_url"] = res["url"]
                    print(f"  published q{c.question_id}/{c.model}: {res['url'] or '(no url in response)'}")
                else:
                    failures.append((f"q{c.question_id}/{c.model}", res["status"],
                                     f"{res['error']} | body: {res['raw'][:300]}"))
                    print(f"  FAILED q{c.question_id}/{c.model}: {res['error']}")
            rows.append(row)

        csv_path = dir_ai.write_published_urls(rows, order_dir / "published_urls.csv")
        print(f"\nURL file: {csv_path}")
        print(f"published={sum(1 for r in rows if r['public_url'])}  failed={len(failures)}  "
              f"total={len(rows)}")
        if failures:
            print("\nFailures (exact API response):")
            for name, status, err in failures:
                print(f"  {name}: status={status} {err}")
            return 1
        return 0
    elif args.command == "publish-prepare":
        from . import publish as publish_mod
        if not args.client_slug:
            print("ERROR: pass --input (Directory Article API mode) or --client-slug "
                  "(static-site mode).", file=sys.stderr)
            return 1
        try:
            pub_root, plan = publish_mod.prepare_publish(
                args.out, args.client_slug, args.order_id,
                public_base_url=args.public_base_url,
                include_screenshots=not args.no_screenshots,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"Publish-ready folder: {pub_root}")
        print(f"  pages:       {len(plan.urls('page'))}")
        print(f"  screenshots: {len(plan.urls('screenshot'))}")
        print(f"  sitemap:     {len(plan.urls('sitemap'))}")
        print(f"  remote path structure: <remote_root>/{args.client_slug}/{args.order_id}/")
        print(f"  config template:       {pub_root / 'publish.config.example.json'}")
        print(f"  what to fill in:       {pub_root / 'PUBLISH_README.md'}")
        print("\nPublish once credentials are configured:")
        print(f"  python -m engine.main publish --client-slug {args.client_slug} "
              f"--order-id {args.order_id} --config <your-config.json> --out {args.out}")
        return 0
    elif args.command == "publish":
        from . import publish as publish_mod
        if not (args.client_slug and args.config):
            print("ERROR: pass --input (Directory Article API mode) or "
                  "--client-slug with --config (static-site mode).", file=sys.stderr)
            return 1
        try:
            result = publish_mod.publish(
                args.out, args.client_slug, args.order_id, args.config, dry_run=args.dry_run)
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        if result.get("dry_run"):
            print(f"\nDry run complete: {result['count']} file(s) would be published.")
        elif result.get("urls"):
            print(f"Published {result['count']} file(s) to {result['public_base_url']}")
            print(f"  URLs recorded in: {Path(args.out) / args.client_slug / args.order_id / 'published_urls.txt'}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
