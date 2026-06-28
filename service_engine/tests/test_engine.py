"""Tests for the AI Mention engine. Run: python -m pytest -q"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from engine import extractor, generator, pages, report
from engine.models import PACKAGES, ClientInput, Question, ResponseRow


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
