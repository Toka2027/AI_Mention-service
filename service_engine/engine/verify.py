"""QA gate (run before sending any deliverable).

Verifies one order folder against the delivery checklist and returns PASS / WARN /
FAIL per check plus an overall gate. Wired to the CLI as:

    python -m engine.main verify --client-slug <slug> --order-id <id>

The gate fails (exit 1) on any FAIL; WARNs do not block but must be reviewed.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .models import PACKAGES, ResponseRow
from .pages import slugify

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"

# Promise-style wording we must never ship (banned positive claims). Disclaimers
# that negate these ("does not guarantee...") are allowed and filtered out.
_PROMISE_PATTERNS = [
    r"guarantee\w*\b[^.\n]{0,30}\b(ai|llm|mention|ranking|rankings|index|indexing|visibility)",
    r"\binject\w*\b[^.\n]{0,20}\bsignal",
    r"\bseed\w*\b[^.\n]{0,15}\bsignal",
    r"manipulat\w*\b[^.\n]{0,20}\b(ai|answer|model|llm|result)",
    r"\bforc\w*\b[^.\n]{0,20}\b(ai|mention|model|llm)",
    r"\binfluenc\w*\b[^.\n]{0,20}\b(ai|model|llm)",
    r"\btrain\w*\b[^.\n]{0,20}\b(the\s+)?(model|ai|llm)",
]
_NEG_TOKENS = (
    "not", "never", "no ", "without", "n't", "avoid", "cannot", "do not", "does not", "don't",
)
_PNG_RE = re.compile(r"^q\d+_[a-z0-9]+(_part\d+)?\.png$")
_INTAKE_RE = re.compile(r"intake completeness:\s*(\d+)\s*/\s*(\d+)", re.IGNORECASE)


def _add(checks: list[dict], name: str, status: str, detail: str) -> None:
    checks.append({"name": name, "status": status, "detail": detail})


def _read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _scan_banned(order_dir: Path) -> list[str]:
    """Return human-readable hits of unguarded promise wording in client-facing copy.

    A match is treated as a disclaimer (allowed) when its *sentence* contains a
    negation token. The sentence is the span back to the previous '.', '!' or '?'
    (newlines are ignored so wrapped disclaimers are scoped correctly)."""
    hits: list[str] = []
    for p in sorted(order_dir.rglob("*")):
        if p.suffix.lower() not in (".md", ".txt", ".html"):
            continue
        low = p.read_text(encoding="utf-8", errors="ignore").lower()
        for pat in _PROMISE_PATTERNS:
            for m in re.finditer(pat, low):
                prev_end = max(low.rfind(ch, 0, m.start()) for ch in ".!?")
                sentence = low[prev_end + 1: m.start()]
                if any(neg in sentence for neg in _NEG_TOKENS):
                    continue  # negated => a disclaimer, allowed
                rel = p.relative_to(order_dir).as_posix()
                hits.append(f"{rel}: '{m.group(0).strip()}'")
    return hits


def verify_order(
    out_root: str,
    client_slug: str,
    order_id: str,
    min_intake: int = 8,
    strict_screenshots: bool = False,
) -> dict:
    slug = slugify(client_slug)
    oid = slugify(order_id)
    order_dir = Path(out_root) / slug / oid
    checks: list[dict] = []

    if not order_dir.exists():
        _add(checks, "order folder", FAIL, f"not found: {order_dir}")
        return {"order_dir": str(order_dir), "checks": checks, "overall": FAIL}

    # 1. Required artifacts exist.
    required = [
        "order_brief.md", "questions.csv", "questions.json", "responses_template.csv",
        "master_table.csv", "source_frequency.csv", "competitor_frequency.csv",
        "report.pdf", "sitemap.xml", "support_page_urls.txt", "source_links.csv",
        "submission_checklist.md", "manifest.json",
    ]
    for fname in required:
        f = order_dir / fname
        _add(checks, f"file: {fname}", PASS if f.exists() and f.stat().st_size > 0 else FAIL,
             "present" if f.exists() else "MISSING")

    pages_dir = order_dir / "pages"
    page_files = sorted(pages_dir.glob("*.html")) if pages_dir.exists() else []
    _add(checks, "support pages exist", PASS if page_files else FAIL,
         f"{len(page_files)} page(s)")

    zip_path = order_dir.parent / f"{oid}_deliverable.zip"
    _add(checks, "ZIP deliverable exists", PASS if zip_path.exists() else FAIL,
         str(zip_path) if zip_path.exists() else "MISSING")

    # Load manifest (order metadata) for the remaining checks.
    manifest = {}
    mpath = order_dir / "manifest.json"
    if mpath.exists():
        try:
            manifest = json.loads(mpath.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            _add(checks, "manifest readable", FAIL, "manifest.json is not valid JSON")
    order_meta = manifest.get("order", {}) if isinstance(manifest, dict) else {}
    package = order_meta.get("package", "")

    # 2. Question count matches package.
    qcsv = order_dir / "questions.csv"
    if qcsv.exists() and package in PACKAGES:
        n_q = len(_read_csv_rows(qcsv))
        want = PACKAGES[package].n_questions
        _add(checks, "question count matches package", PASS if n_q == want else FAIL,
             f"{n_q} questions vs {package} expects {want}")
    else:
        _add(checks, "question count matches package", WARN, "could not resolve package/questions")

    # 3. Responses (master table) match generated questions.
    mt = order_dir / "master_table.csv"
    if qcsv.exists() and mt.exists():
        q_ids = {r["id"] for r in _read_csv_rows(qcsv)}
        m_rows = _read_csv_rows(mt)
        m_ids = {r["question_id"] for r in m_rows}
        _add(checks, "responses match questions", PASS if q_ids == m_ids else FAIL,
             "aligned" if q_ids == m_ids
             else f"mismatch (only-in-questions={sorted(q_ids - m_ids)}, only-in-master={sorted(m_ids - q_ids)})")
    else:
        m_rows = []
        _add(checks, "responses match questions", FAIL, "missing questions.csv or master_table.csv")

    # 4. Intake score acceptable.
    brief = order_dir / "order_brief.md"
    if brief.exists():
        m = _INTAKE_RE.search(brief.read_text(encoding="utf-8"))
        if m:
            filled, total = int(m.group(1)), int(m.group(2))
            status = PASS if filled >= min_intake else WARN
            _add(checks, "intake completeness", status,
                 f"{filled}/{total} (threshold {min_intake})")
        else:
            _add(checks, "intake completeness", WARN, "could not parse from order_brief.md")
    else:
        _add(checks, "intake completeness", FAIL, "order_brief.md missing")

    # 5. Screenshots exist + naming + full-page rules.
    shots_dir = order_dir / "screenshots"
    pngs = [p.name for p in shots_dir.glob("*.png")] if shots_dir.exists() else []
    captured_expected, missing_captured, pending = [], [], []
    for r in m_rows:
        fname = f"q{r['question_id']}_{r['model'].lower()}.png"
        if (r.get("answer_excerpt") or "") != ResponseRow.PENDING:
            captured_expected.append(fname)
            if fname not in pngs:
                missing_captured.append(fname)
        else:
            if fname not in pngs:
                pending.append(fname)
    if missing_captured:
        _add(checks, "captured-answer screenshots present", FAIL,
             f"missing {len(missing_captured)}: {missing_captured[:5]}{'...' if len(missing_captured) > 5 else ''}")
    else:
        _add(checks, "captured-answer screenshots present", PASS,
             f"{len(captured_expected)} present")
    if pending:
        _add(checks, "manual screenshots present", FAIL if strict_screenshots else WARN,
             f"{len(pending)} full-page screenshot(s) still to capture")
    else:
        _add(checks, "manual screenshots present", PASS, "all expected screenshots present")

    strays = [n for n in pngs if not _PNG_RE.match(n)]
    _add(checks, "screenshot naming", PASS if not strays else WARN,
         "all match q{id}_{model}.png" if not strays else f"non-conforming: {strays[:5]}")

    ef = shots_dir / "EXPECTED_FILES.txt"
    fullpage_ok = ef.exists() and "FULL-PAGE" in ef.read_text(encoding="utf-8", errors="ignore")
    _add(checks, "full-page rules + fallback documented", PASS if fullpage_ok else WARN,
         "EXPECTED_FILES.txt documents full-page rules + fallback" if fullpage_ok
         else "screenshot rules manifest missing")

    # 6. Client-safe wording / no banned language.
    banned = _scan_banned(order_dir)
    _add(checks, "client-safe wording (no banned promises)", PASS if not banned else FAIL,
         "clean" if not banned else f"{len(banned)} hit(s): {banned[:3]}")

    # 7. No cross-client data mixing.
    mix_problems = []
    if order_meta.get("client_slug") and order_meta["client_slug"] != slug:
        mix_problems.append(f"manifest client_slug={order_meta['client_slug']} != {slug}")
    if order_meta.get("order_id") and order_meta["order_id"] != oid:
        mix_problems.append(f"manifest order_id={order_meta['order_id']} != {oid}")
    if brief.exists() and oid not in slugify(brief.read_text(encoding="utf-8")):
        mix_problems.append("order_brief.md does not reference this order id")
    foreign_pages = [p.name for p in page_files if not p.name.startswith(slug)]
    if foreign_pages:
        mix_problems.append(f"pages not prefixed with client slug: {foreign_pages[:3]}")
    _add(checks, "no cross-client data mixing", PASS if not mix_problems else FAIL,
         "consistent" if not mix_problems else "; ".join(mix_problems))

    statuses = {c["status"] for c in checks}
    overall = FAIL if FAIL in statuses else (WARN if WARN in statuses else PASS)
    return {"order_dir": str(order_dir), "checks": checks, "overall": overall}


def format_report(result: dict) -> str:
    icon = {PASS: "[PASS]", WARN: "[WARN]", FAIL: "[FAIL]"}
    lines = [f"QA gate for: {result['order_dir']}", ""]
    for c in result["checks"]:
        lines.append(f"  {icon[c['status']]:7} {c['name']}: {c['detail']}")
    lines.append("")
    lines.append(f"OVERALL: {result['overall']}")
    if result["overall"] == FAIL:
        lines.append("=> DO NOT DELIVER. Fix the [FAIL] items and re-run verify.")
    elif result["overall"] == WARN:
        lines.append("=> Review the [WARN] items (e.g. pending manual screenshots) before delivery.")
    else:
        lines.append("=> Ready to deliver.")
    return "\n".join(lines)
