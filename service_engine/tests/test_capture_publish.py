"""Tests for the real-browser capture evidence QA and the publishing layer.

These cover everything around the browser except the browser itself: the strict
proof rules that decide whether a capture counts as real, and the publish-ready
tree + upload. The browser session itself is exercised by the operator smoke test
(`capture --smoke`), which needs a real signed-in UI.
"""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

from engine import generator, publish
from engine.capture import qa
from engine.capture.runner import _parse_range
from engine.models import ClientInput


def _write_input(tmp_path: Path) -> Path:
    """Client input with full recommended intake, so intake checks are not the blocker."""
    data = {
        "order_id": "ord-p", "brand": "Acme Co", "brand_variations": ["Acme", "ACME"],
        "website": "https://acme.example", "niche": "widget services", "country": "US",
        "language": "English", "keywords": ["blue widgets", "red widgets", "green widgets"],
        "package": "BASIC", "competitors_known": ["WidgetCo"],
        "target_urls": ["https://acme.example"], "preferred_positioning": "Reliable widgets",
        "services_to_highlight": ["blue widgets"], "topics_to_avoid": ["ranking guarantees"],
        "compliance_notes": "Factual only.", "delivery_contact": "ops@acme.example",
    }
    p = tmp_path / "acme_full.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _png(path: Path, w: int = 1440, h: int = 3200) -> None:
    """Write a real, valid PNG of the given size (so QA's checks are exercised)."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes([(x * 7) % 256 for x in range(w * 3)]) for _ in range(h))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                     + chunk(b"IDAT", zlib.compress(raw, 1)) + chunk(b"IEND", b""))


def _good_capture(caps: Path, shots: Path, model: str, qid: int, prompt: str) -> None:
    """Write exactly what a successful browser capture leaves behind."""
    mdir = caps / model
    mdir.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)
    (mdir / f"q{qid}.txt").write_text("A" * 400, encoding="utf-8")
    (mdir / f"q{qid}.evidence.txt").write_text("browser", encoding="utf-8")
    (mdir / f"q{qid}.capture.json").write_text(json.dumps({
        "question_id": qid, "model": model, "evidence_type": "browser",
        "captured_at": "2026-07-27T10:00:00+00:00",
        "page_url": "https://chatgpt.com/c/abc-123", "browser": "chrome",
        "submitted_prompt": prompt, "answer_chars": 400,
    }), encoding="utf-8")
    _png(shots / f"q{qid}_{model}.png")


# --- question range parsing --------------------------------------------------

def test_parse_range_handles_lists_ranges_and_bounds():
    assert _parse_range(None, 25) == list(range(1, 26))
    assert _parse_range("1", 25) == [1]
    assert _parse_range("1-3,7", 25) == [1, 2, 3, 7]
    assert _parse_range("24-99", 25) == [24, 25]  # clamped to the question count


# --- strict capture QA -------------------------------------------------------

def test_capture_qa_passes_on_a_real_browser_capture(tmp_path: Path):
    inp = _write_input(tmp_path)
    ci = ClientInput.from_json(str(inp))
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    caps, shots = tmp_path / "caps", tmp_path / "shots"
    _good_capture(caps, shots, "chatgpt", qs[0].id, qs[0].text)

    res = qa.verify_capture(caps, shots, "chatgpt", [qs[0].id], {q.id: q.text for q in qs})
    assert res["overall"] == qa.PASS, qa.format_report(res)


def test_capture_qa_fails_when_evidence_is_not_browser(tmp_path: Path):
    inp = _write_input(tmp_path)
    ci = ClientInput.from_json(str(inp))
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    caps, shots = tmp_path / "caps", tmp_path / "shots"
    _good_capture(caps, shots, "chatgpt", qs[0].id, qs[0].text)
    # An in-session / proof-card answer must never pass as browser proof.
    (caps / "chatgpt" / f"q{qs[0].id}.evidence.txt").write_text(
        "model-authored-insession", encoding="utf-8")

    res = qa.verify_capture(caps, shots, "chatgpt", [qs[0].id], {q.id: q.text for q in qs})
    assert res["overall"] == qa.FAIL
    check = next(c for c in res["cells"][0]["checks"] if c["name"].startswith("evidence type"))
    assert check["status"] == qa.FAIL


def test_capture_qa_fails_when_screenshot_missing(tmp_path: Path):
    inp = _write_input(tmp_path)
    ci = ClientInput.from_json(str(inp))
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    caps, shots = tmp_path / "caps", tmp_path / "shots"
    _good_capture(caps, shots, "chatgpt", qs[0].id, qs[0].text)
    (shots / f"q{qs[0].id}_chatgpt.png").unlink()

    res = qa.verify_capture(caps, shots, "chatgpt", [qs[0].id], {q.id: q.text for q in qs})
    assert res["overall"] == qa.FAIL


def test_capture_qa_fails_on_wrong_host_or_wrong_prompt(tmp_path: Path):
    inp = _write_input(tmp_path)
    ci = ClientInput.from_json(str(inp))
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    qid, qtexts = qs[0].id, {q.id: q.text for q in qs}

    # A page URL that is not on the model's real host is not proof of that model.
    caps, shots = tmp_path / "c1", tmp_path / "s1"
    _good_capture(caps, shots, "chatgpt", qid, qs[0].text)
    prov = json.loads((caps / "chatgpt" / f"q{qid}.capture.json").read_text())
    prov["page_url"] = "https://example.com/fake"
    (caps / "chatgpt" / f"q{qid}.capture.json").write_text(json.dumps(prov))
    res = qa.verify_capture(caps, shots, "chatgpt", [qid], qtexts)
    assert res["overall"] == qa.FAIL
    assert next(c for c in res["cells"][0]["checks"] if "host" in c["name"])["status"] == qa.FAIL

    # A submitted prompt that is not the generated question is not proof either.
    caps2, shots2 = tmp_path / "c2", tmp_path / "s2"
    _good_capture(caps2, shots2, "chatgpt", qid, "some other prompt entirely")
    res2 = qa.verify_capture(caps2, shots2, "chatgpt", [qid], qtexts)
    assert res2["overall"] == qa.FAIL
    assert next(c for c in res2["cells"][0]["checks"]
                if "submitted prompt" in c["name"])["status"] == qa.FAIL


def test_capture_qa_fails_on_a_stub_screenshot(tmp_path: Path):
    """A tiny/non-PNG file must not pass as a real full-page browser screenshot."""
    inp = _write_input(tmp_path)
    ci = ClientInput.from_json(str(inp))
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    caps, shots = tmp_path / "caps", tmp_path / "shots"
    _good_capture(caps, shots, "chatgpt", qs[0].id, qs[0].text)
    (shots / f"q{qs[0].id}_chatgpt.png").write_bytes(b"REAL")  # not a PNG

    res = qa.verify_capture(caps, shots, "chatgpt", [qs[0].id], {q.id: q.text for q in qs})
    assert res["overall"] == qa.FAIL


# --- publishing --------------------------------------------------------------

def _built_order(tmp_path: Path) -> tuple[Path, str, str]:
    from engine import main as engine_main
    from engine import report

    inp = _write_input(tmp_path)
    ci = ClientInput.from_json(str(inp))
    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    rows = generator.build_capture_template(qs, ci.pkg.models)
    for r in rows:
        r.answer = f"Captured answer for q{r.question_id} from {r.model}."
        r.evidence_type = "browser"
    resp = tmp_path / "resp.csv"
    report.write_capture_template(rows, qs, resp)
    out = tmp_path / "outputs"
    engine_main.run(str(inp), str(resp), str(out), order_id="ord-p")
    return out, "acme-co", "ord-p"


def test_prepare_publish_builds_tree_urls_and_config(tmp_path: Path):
    out, slug, oid = _built_order(tmp_path)
    pub_root, plan = publish.prepare_publish(
        out, slug, oid, public_base_url="https://oursite.example/ai")

    assert (pub_root / "publish_manifest.json").exists()
    assert (pub_root / "publish.config.example.json").exists()
    assert (pub_root / "PUBLISH_README.md").exists()
    assert plan.urls("page"), "expected support pages in the publish set"
    assert all(u.startswith(f"https://oursite.example/ai/{slug}/{oid}/") for u in plan.urls())

    # The sitemap must list the FINAL public URLs, not the client's own domain.
    sitemap = (pub_root / "public" / slug / oid / "sitemap.xml").read_text(encoding="utf-8")
    for url in plan.urls("page"):
        assert url in sitemap


def test_publish_local_copies_files_and_records_urls(tmp_path: Path):
    out, slug, oid = _built_order(tmp_path)
    publish.prepare_publish(out, slug, oid, public_base_url="https://oursite.example/ai")

    webroot = tmp_path / "webroot"
    cfg = tmp_path / "publish.config.json"
    cfg.write_text(json.dumps({
        "site": "https://oursite.example", "public_base_url": "https://oursite.example/ai",
        "method": "local", "remote_root": str(webroot),
    }), encoding="utf-8")

    result = publish.publish(out, slug, oid, cfg)
    assert result["count"] > 0
    assert (webroot / slug / oid / "sitemap.xml").exists()
    # Public URLs are recorded back into the order folder for the report.
    urls_file = out / slug / oid / "published_urls.txt"
    assert urls_file.exists()
    assert len(urls_file.read_text(encoding="utf-8").strip().splitlines()) == result["count"]


def test_publish_blocks_on_missing_credentials(tmp_path: Path):
    out, slug, oid = _built_order(tmp_path)
    publish.prepare_publish(out, slug, oid, public_base_url="https://oursite.example/ai")
    cfg = tmp_path / "bad.config.json"
    cfg.write_text(json.dumps({"method": "sftp", "public_base_url": "https://x.example"}),
                   encoding="utf-8")

    try:
        publish.publish(out, slug, oid, cfg)
    except ValueError as exc:
        assert "host" in str(exc) and "username" in str(exc)
    else:
        raise AssertionError("publish must refuse to run with an incomplete config")


# --- S3 upload safety --------------------------------------------------------

def test_unsafe_screenshots_are_never_uploaded(tmp_path, monkeypatch):
    """A public asset cannot be un-published, so unsafe captures must not go up."""
    from engine import s3_upload

    cfg = tmp_path / "s3.json"
    cfg.write_text(json.dumps({
        "endpoint": "https://b.nbg1.your-objectstorage.com", "bucket": "b",
        "region": "nbg1", "access_key": "x", "secret_key": "y",
    }), encoding="utf-8")
    monkeypatch.setenv(s3_upload.CONFIG_ENV, str(cfg))

    shot = tmp_path / "q2_gemini.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")
    rows = s3_upload.upload_screenshots([
        {"query_id": "q1", "model": "ChatGPT", "screenshot_path": str(shot),
         "safe_to_share": "yes"},
        {"query_id": "q2", "model": "Gemini", "screenshot_path": str(shot),
         "safe_to_share": "no"},
    ], "acme", "ord-1", dry_run=True)

    unsafe = next(r for r in rows if r["query_id"] == "q2")
    assert unsafe["public_image_url"] == "", "an unsafe capture must get no public URL"
    assert "SKIPPED" in unsafe["uploaded_at"]
    safe = next(r for r in rows if r["query_id"] == "q1")
    assert safe["public_image_url"].startswith("https://")


def test_s3_config_summary_masks_secrets(tmp_path, monkeypatch):
    from engine import s3_upload

    cfg = tmp_path / "s3.json"
    cfg.write_text(json.dumps({
        "endpoint": "https://b.nbg1.your-objectstorage.com", "bucket": "b",
        "region": "nbg1", "access_key": "SUPERSECRETACCESS",
        "secret_key": "SUPERSECRETSECRET",
    }), encoding="utf-8")
    monkeypatch.setenv(s3_upload.CONFIG_ENV, str(cfg))

    blob = json.dumps(s3_upload.safe_config_summary())
    assert "SUPERSECRETACCESS" not in blob
    assert "SUPERSECRETSECRET" not in blob
    assert "masked" in blob


def test_aimention_prefix_cannot_collide_with_blog_assets(tmp_path, monkeypatch):
    from engine import s3_upload
    key = s3_upload.object_key("1billionlinks", "2026-06-28-001", "q1_chatgpt.png")
    assert key.startswith(s3_upload.AIMENTION_PREFIX + "/")
    assert "captcharank" not in key
