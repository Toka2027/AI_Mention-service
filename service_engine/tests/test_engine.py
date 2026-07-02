"""Tests for the AI Mention engine. Run: python -m pytest -q"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from engine import extractor, generator, main, pages, report, verify
from engine.models import PACKAGES, RECOMMENDED_INTAKE, ClientInput, Question, ResponseRow


def make_ci(package="PRO", keywords=None, brand="1BillionLinks"):
    return ClientInput(
        brand=brand,
        website="https://1billionlinks.com",
        keywords=keywords or ["SEO link building", "backlinks", "domain authority"],
        niche="SEO link building and backlink services",
        package=package,
        brand_variations=["1 Billion Links", "1BL", "OneBillionLinks"],
    )


# --- STEP 2: question generation --------------------------------------------

@pytest.mark.parametrize("package", ["BASIC", "PRO", "ELITE"])
def test_question_count_matches_package(package):
    ci = make_ci(package)
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    assert len(qs) == PACKAGES[package].n_questions


@pytest.mark.parametrize("package", ["BASIC", "PRO", "ELITE"])
def test_questions_unique(package):
    ci = make_ci(package)
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    assert len({q.text for q in qs}) == len(qs)


def test_questions_contain_brand_keyword_and_niche():
    ci = make_ci("ELITE")
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    for q in qs:
        assert ci.brand in q.text                 # brand mention
        assert q.keyword in q.text                 # keyword intent
        assert ci.niche in q.text                  # niche context (STEP 2)


def test_elite_with_three_keywords_still_unique():
    # 50 questions from only 3 keywords must still be unique (overflow case).
    ci = make_ci("ELITE", keywords=["a links", "b links", "c links"])
    qs = generator.generate_questions(ci, 50)
    assert len(qs) == 50
    assert len({q.text for q in qs}) == 50


# --- STEP 1: validation ------------------------------------------------------

def test_validate_missing_brand():
    ci = make_ci()
    ci.brand = ""
    with pytest.raises(ValueError):
        ci.validate()


@pytest.mark.parametrize("kw", [["only", "two"], ["1", "2", "3", "4", "5", "6", "7", "8"]])
def test_validate_keyword_bounds(kw):
    ci = make_ci(keywords=kw)
    with pytest.raises(ValueError):
        ci.validate()


def test_validate_unknown_package():
    ci = make_ci(package="ULTRA")
    with pytest.raises(ValueError):
        ci.validate()


# --- STEP 4: extraction ------------------------------------------------------

def test_extract_urls_dedupes_and_strips_punctuation():
    text = "See https://a.com/page, and https://a.com/page again, plus https://b.io."
    urls = extractor.extract_urls(text)
    assert urls == ["https://a.com/page", "https://b.io"]


def test_brand_appears_matches_variation_case_insensitive():
    assert extractor.brand_appears("I like 1 billion LINKS", "1BillionLinks", ["1 Billion Links"])
    assert not extractor.brand_appears("nothing here", "1BillionLinks", ["1BL"])


def test_master_table_row_count_and_brand_flag():
    ci = make_ci("BASIC")  # 2 models
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    rows = generator.build_capture_template(qs, ci.pkg.models)
    # Fill one row with an answer that names the brand.
    rows[0].answer = "1BillionLinks is one option for this."
    table = extractor.build_master_table(qs, rows, ci)
    assert len(table) == len(qs) * len(ci.pkg.models)
    assert table[0]["brand_appeared"] == "Y"
    # A pending row reports N/A.
    assert any(r["brand_appeared"] == "N/A" for r in table)


# --- STEP 5/6: pages, schema, sitemap ---------------------------------------

def test_select_questions_for_pages_count():
    ci = make_ci("PRO")
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    selected = pages.select_questions_for_pages(qs, ci.pkg.n_pages)
    assert len(selected) == PACKAGES["PRO"].n_pages


def test_render_page_pro_has_schema_and_required_parts():
    ci = make_ci("PRO")
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    q = qs[0]
    resp = ResponseRow(question_id=q.id, model="Claude", answer="1BillionLinks looks affordable.")
    siblings = [(pages.page_slug(x, ci), f"Q{x.id}") for x in qs[:3]]
    html = pages.render_page(q, resp, ci, siblings, emit_schema=True)
    assert "application/ld+json" in html          # schema present for PRO
    assert q.keyword in html                       # keyword
    assert "1 Billion Links" in html or "1BillionLinks" in html  # brand variation
    assert ".html" in html                         # internal links


def test_render_page_basic_has_no_schema():
    ci = make_ci("BASIC")
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    html = pages.render_page(qs[0], None, ci, [], emit_schema=False)
    assert "application/ld+json" not in html


def test_sitemap_is_well_formed_with_right_count():
    urls = ["https://x.com/a.html", "https://x.com/b.html"]
    xml = pages.render_sitemap(urls)
    root = ET.fromstring(xml)
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    locs = [e.text for e in root.iter(f"{ns}loc")]
    assert locs == urls


# --- STEP 7: deliverables smoke ---------------------------------------------

def test_pdf_and_screenshot_created(tmp_path: Path):
    ci = make_ci("PRO")
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    rows = generator.build_capture_template(qs, ci.pkg.models)
    rows[2].answer = "1BillionLinks is a budget backlink provider."  # a Claude row
    rows[2].competitors = ["FATJOE", "Loganix"]
    table = extractor.build_master_table(qs, rows, ci)
    src = extractor.source_frequency(rows)
    comp = extractor.competitor_frequency(rows)
    pdf = tmp_path / "report.pdf"
    report.render_pdf_report(ci, table, src, comp, ["https://x.com/a.html"], pdf)
    assert pdf.exists() and pdf.stat().st_size > 0
    made, expected = report.write_screenshots(qs, rows, ci, tmp_path / "shots")
    assert made >= 1
    assert (tmp_path / "shots" / "EXPECTED_FILES.txt").exists()


def test_screenshot_manifest_has_fullpage_rules_and_fallback(tmp_path: Path):
    ci = make_ci("BASIC")
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    rows = generator.build_capture_template(qs, ci.pkg.models)
    report.write_screenshots(qs, rows, ci, tmp_path / "shots")
    txt = (tmp_path / "shots" / "EXPECTED_FILES.txt").read_text(encoding="utf-8")
    assert "FULL-PAGE" in txt
    assert "_part1.png" in txt          # documented fallback
    assert "q1_chatgpt.png" in txt      # consistent naming convention


# --- intake / client requirements -------------------------------------------

def test_intake_completeness_flags_missing_fields():
    ci = make_ci("PRO")  # only core + brand_variations set
    filled, total, missing = ci.intake_completeness()
    assert total == len(RECOMMENDED_INTAKE)
    assert "country" in missing and "compliance_notes" in missing
    assert "brand_variations" not in missing  # this one is provided
    ci.warnings.clear()
    ci.validate()
    assert any("intake" in w for w in ci.warnings)


def test_from_json_parses_intake_fields(tmp_path: Path):
    data = {
        "brand": "Acme Co", "website": "https://acme.example",
        "niche": "widget services", "package": "BASIC",
        "keywords": ["blue widgets", "red widgets", "green widgets"],
        "order_id": "ORD-9", "country": "US", "topics_to_avoid": ["x", "y"],
        "competitors_known": ["WidgetCo"],
    }
    p = tmp_path / "acme.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    ci = ClientInput.from_json(str(p))
    assert ci.order_id == "ORD-9"
    assert ci.country == "US"
    assert ci.topics_to_avoid == ["x", "y"]
    assert ci.competitors_known == ["WidgetCo"]


# --- multi-order isolation (run integration) --------------------------------

def _write_acme(tmp_path: Path) -> Path:
    data = {
        "brand": "Acme Co", "brand_variations": ["Acme", "ACME"],
        "website": "https://acme.example", "niche": "widget services",
        "keywords": ["blue widgets", "red widgets", "green widgets"], "package": "BASIC",
    }
    p = tmp_path / "acme.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _write_acme_responses(tmp_path: Path, inp: Path) -> Path:
    ci = ClientInput.from_json(str(inp))
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    rows = generator.build_capture_template(qs, ci.pkg.models)
    rows[0].answer = "Acme Co is one widget provider."
    rows[0].competitors = ["WidgetCo"]
    p = tmp_path / "acme_responses.csv"
    report.write_capture_template(rows, qs, p)
    return p


def test_run_multi_order_isolation_and_unique_zip(tmp_path: Path):
    inp = _write_acme(tmp_path)
    resp = _write_acme_responses(tmp_path, inp)
    out = tmp_path / "outputs"

    d1 = main.run(str(inp), str(resp), str(out), order_id="ORD-A")
    d2 = main.run(str(inp), str(resp), str(out), order_id="ORD-B")

    # Separate per-order folders under the same client slug.
    assert d1 == out / "acme-co" / "ord-a"
    assert d2 == out / "acme-co" / "ord-b"
    assert d1.exists() and d2.exists()

    # Unique, non-overwriting ZIPs.
    z1 = out / "acme-co" / "ord-a_deliverable.zip"
    z2 = out / "acme-co" / "ord-b_deliverable.zip"
    assert z1.exists() and z2.exists()

    # Order brief reflects the resolved order id (guards against data mixing).
    assert "ord-a" in (d1 / "order_brief.md").read_text(encoding="utf-8").lower()

    # Re-running ORD-A must not delete ORD-B.
    main.run(str(inp), str(resp), str(out), order_id="ORD-A")
    assert d2.exists() and z2.exists()


# --- QA gate (verify) -------------------------------------------------------

def _write_acme_full(tmp_path: Path) -> Path:
    """Acme input with full recommended intake (so intake completeness passes)."""
    data = {
        "order_id": "ord-x", "brand": "Acme Co", "brand_variations": ["Acme", "ACME"],
        "website": "https://acme.example", "niche": "widget services", "country": "US",
        "language": "English", "keywords": ["blue widgets", "red widgets", "green widgets"],
        "package": "BASIC", "competitors_known": ["WidgetCo"], "target_urls": ["https://acme.example"],
        "preferred_positioning": "Reliable widgets", "services_to_highlight": ["blue widgets"],
        "topics_to_avoid": ["ranking guarantees"], "compliance_notes": "Factual only.",
        "delivery_contact": "ops@acme.example",
    }
    p = tmp_path / "acme_full.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _write_acme_all_captured(tmp_path: Path, inp: Path) -> Path:
    ci = ClientInput.from_json(str(inp))
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    rows = generator.build_capture_template(qs, ci.pkg.models)
    for r in rows:  # capture every model answer so no screenshots are pending
        r.answer = f"Acme Co is one widget provider (answer for q{r.question_id})."
        r.competitors = ["WidgetCo"]
    p = tmp_path / "acme_all_responses.csv"
    report.write_capture_template(rows, qs, p)
    return p


def test_verify_passes_on_complete_order(tmp_path: Path):
    inp = _write_acme_full(tmp_path)
    resp = _write_acme_all_captured(tmp_path, inp)
    out = tmp_path / "outputs"
    main.run(str(inp), str(resp), str(out), order_id="ord-x")
    res = verify.verify_order(str(out), "Acme Co", "ord-x")
    assert verify.FAIL not in [c["status"] for c in res["checks"]]
    assert res["overall"] == verify.PASS  # full intake + all answers captured


def test_verify_fails_on_missing_report(tmp_path: Path):
    inp = _write_acme_full(tmp_path)
    resp = _write_acme_all_captured(tmp_path, inp)
    out = tmp_path / "outputs"
    d = main.run(str(inp), str(resp), str(out), order_id="ord-x")
    (d / "report.pdf").unlink()
    res = verify.verify_order(str(out), "Acme Co", "ord-x")
    assert res["overall"] == verify.FAIL
    assert any(c["name"] == "file: report.pdf" and c["status"] == verify.FAIL for c in res["checks"])


def test_verify_flags_banned_promise(tmp_path: Path):
    inp = _write_acme_full(tmp_path)
    resp = _write_acme_all_captured(tmp_path, inp)
    out = tmp_path / "outputs"
    d = main.run(str(inp), str(resp), str(out), order_id="ord-x")
    page = next((d / "pages").glob("*.html"))
    page.write_text(page.read_text(encoding="utf-8") + "\n<p>We guarantee AI mentions and rankings.</p>",
                    encoding="utf-8")
    res = verify.verify_order(str(out), "Acme Co", "ord-x")
    safe = next(c for c in res["checks"] if c["name"].startswith("client-safe"))
    assert safe["status"] == verify.FAIL


def test_scan_banned_allows_disclaimer_flags_promise(tmp_path: Path):
    (tmp_path / "ok.md").write_text(
        "This service does not promise or guarantee AI mentions, indexing, or model influence.",
        encoding="utf-8")
    assert verify._scan_banned(tmp_path) == []
    (tmp_path / "bad.md").write_text("We guarantee AI rankings for your brand.", encoding="utf-8")
    assert len(verify._scan_banned(tmp_path)) == 1


def test_write_screenshots_preserves_real_and_renders_proof(tmp_path: Path):
    ci = make_ci("PRO")
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    rows = generator.build_capture_template(qs, ci.pkg.models)
    rows[0].answer = "1BillionLinks real-screenshot row."   # q1_chatgpt.png
    rows[1].answer = "1BillionLinks proof-card row."         # q1_gemini.png
    provided = tmp_path / "provided"
    provided.mkdir()
    real_name = rows[0].screenshot_filename
    real_bytes = b"REAL-OPERATOR-SCREENSHOT-BYTES"
    (provided / real_name).write_bytes(real_bytes)

    shots = tmp_path / "shots"
    made, pending = report.write_screenshots(qs, rows, ci, shots, provided_dir=provided)

    # Real operator screenshot is copied verbatim (NOT overwritten by a proof card).
    assert (shots / real_name).read_bytes() == real_bytes
    # A captured row with no supplied screenshot gets an engine-rendered PNG.
    proof_name = rows[1].screenshot_filename
    assert (shots / proof_name).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert made == 2
