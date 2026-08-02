"""Tests for Directory Article API payloads and the two-model scoped delivery.

The rules these protect are the ones that would do real damage if broken: the API key
must never leave the environment, unsafe answers must never reach client-facing
output, and only real browser captures may be included.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from engine import delivery, dir_ai
from engine.models import Question


def _payload(**kw):
    base = dict(
        brand="1BillionLinks", website="https://1billionlinks.com", model="chatgpt",
        question_id=1, query="How does 1BillionLinks support SEO workflows?",
        answer="ChatGPT said:\n\n1BillionLinks provides campaign tooling. " + "x" * 400,
        order_id="2026-06-28-001", evidence_type="browser",
        screenshot_path="/shots/q1_chatgpt.png", capture_time="2026-07-27T12:00:00+00:00",
        client_safe=True, keyword="SEO link building",
    )
    base.update(kw)
    return dir_ai.build_payload(**base)


# --- payload shape -----------------------------------------------------------

def test_conversation_uses_text_key_required_by_the_live_api():
    """The live contract renders `text`; publishing with only `content` renders blank."""
    p = _payload()
    assert [m["role"] for m in p["conversation"]] == ["user", "assistant"]
    for m in p["conversation"]:
        assert m["text"], "every message must carry a non-empty `text`"


def test_query_is_carried_verbatim():
    q = "How does 1BillionLinks support SEO workflows?"
    assert _payload(query=q)["conversation"][0]["text"] == q


def test_ui_label_is_stripped_from_published_answer_only():
    p = _payload()
    assert not p["conversation"][1]["text"].lower().startswith("chatgpt said")
    assert p["conversation"][1]["text"].startswith("1BillionLinks provides")
    # the helper is pure - it never rewrites anything on disk
    assert dir_ai.strip_ui_chrome("Gemini said: hello") == "hello"
    assert dir_ai.strip_ui_chrome("1BillionLinks offers x") == "1BillionLinks offers x"


def test_metadata_carries_provenance_and_safety_flag():
    md = _payload(client_safe=False)["metadata"]
    assert md["evidence_type"] == "browser"
    assert md["query_id"] == "q1" and md["order_id"] == "2026-06-28-001"
    assert md["client_safe"] is False
    assert md["capture_time"]
    # The local screenshot path is deliberately absent - see
    # test_local_screenshot_path_is_never_published.
    assert "screenshot_path" not in md


def test_api_key_never_appears_in_a_payload(monkeypatch):
    monkeypatch.setenv(dir_ai.API_KEY_ENV, "super-secret-key-value")
    blob = json.dumps(_payload())
    assert "super-secret-key-value" not in blob
    assert dir_ai.api_key() == "super-secret-key-value"


def test_publish_refuses_without_a_key(monkeypatch):
    monkeypatch.delenv(dir_ai.API_KEY_ENV, raising=False)
    res = dir_ai.post_article(_payload())
    assert res["ok"] is False
    assert dir_ai.API_KEY_ENV in res["error"]
    assert res["url"] == ""


# --- delivery layering -------------------------------------------------------

def _capture(qid: int, model: str, answer: str, tmp: Path) -> delivery.Capture:
    a = tmp / f"q{qid}_{model}.txt"
    a.write_text(answer, encoding="utf-8")
    s = tmp / f"q{qid}_{model}.png"
    s.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 100)
    from engine import sentiment
    v = sentiment.review_answer(answer, "1BillionLinks")
    return delivery.Capture(
        question_id=qid, model=model, query=f"query {qid}", keyword="SEO link building",
        answer=answer, answer_path=a, screenshot_path=s,
        provenance={"captured_at": "2026-07-27T12:00:00+00:00"}, evidence_type="browser",
        sentiment=v["sentiment"], safe=v["safe"], issue=v["issue"], qa_pass=True,
    )


def _delivery(tmp: Path) -> delivery.Delivery:
    safe = ("1BillionLinks provides campaign tooling that helps agencies. It offers "
            "reporting, supports planning and enables structured workflows.")
    unsafe = ("Bulk link-building can trigger algorithmic or manual penalties. To safely "
              "leverage 1BillionLinks it must be isolated to lower, non-risky tiers.")
    d = delivery.Delivery(order_id="ord-1", client_slug="1billionlinks",
                          brand="1BillionLinks", website="https://1billionlinks.com")
    d.captures = [
        _capture(1, "chatgpt", safe, tmp),
        _capture(2, "gemini", safe, tmp),
        _capture(3, "gemini", unsafe, tmp),
    ]
    return d


def test_unsafe_captures_are_separated(tmp_path: Path):
    d = _delivery(tmp_path)
    assert len(d.safe) == 2 and len(d.unsafe) == 1
    assert d.unsafe[0].question_id == 3


def test_client_report_excludes_unsafe_but_discloses_it(tmp_path: Path):
    d = _delivery(tmp_path)
    text = delivery.client_report(d, "2026-07-28")
    assert "excluded" in text.lower(), "the client must be told answers were held back"
    assert "not a full 4-model PRO delivery" in text
    assert "Claude and Perplexity are not included" in text
    assert "non-risky tiers" not in text, "unsafe answer text must not appear"


def test_internal_report_keeps_everything(tmp_path: Path):
    d = _delivery(tmp_path)
    d.blocked = {"claude": {"blocker": "Cloudflare"}, "perplexity": {"blocker": "Cloudflare"}}
    text = delivery.internal_report(d, "2026-07-28")
    assert "INTERNAL ONLY" in text
    assert "BLOCKED" in text
    for m in ("Claude", "Perplexity"):
        assert m in text


def test_package_contains_only_safe_assets(tmp_path: Path):
    d = _delivery(tmp_path)
    out = tmp_path / "pkg"
    result = delivery.assemble(d, out, "2026-07-28")
    names = zipfile.ZipFile(result["zip"]).namelist()
    assert "CLIENT_REPORT.md" in names and "INTERNAL_REPORT.md" in names
    shots = [n for n in names if n.startswith("screenshots/")]
    assert len(shots) == 2, "only the 2 safe screenshots may be packaged"
    assert not any("q3_gemini" in n for n in shots)
    # the exclusion is recorded, not hidden
    assert "EXCLUDED_FROM_CLIENT.md" in names
    excluded = (out / "EXCLUDED_FROM_CLIENT.md").read_text(encoding="utf-8")
    assert "Q3" in excluded


def test_published_urls_csv_columns(tmp_path: Path):
    rows = [{"query_id": "q1", "model": "ChatGPT", "public_url": "https://x.example/a",
             "safe_to_share": "yes", "screenshot_path": "/s.png", "answer_path": "/a.txt"}]
    p = dir_ai.write_published_urls(rows, tmp_path / "published_urls.csv")
    header = p.read_text(encoding="utf-8").splitlines()[0]
    assert header.split(",") == dir_ai.PUBLISHED_COLS


# --- by-name content file (Option 1 route, the one that renders screenshots) ---

def test_content_name_uses_only_allowed_characters():
    import re
    n = dir_ai.content_name("1billionlinks", 7, "ChatGPT")
    assert re.fullmatch(r"[A-Za-z0-9._-]+", n), n
    assert n == "1billionlinks-q7-chatgpt"


def test_txt_file_follows_the_documented_layout():
    p = _payload()
    name = "1billionlinks-q1-chatgpt"
    txt = dir_ai.build_txt_file(p, name, "2026-07-27T12:00:00+00:00")
    lines = txt.splitlines()
    # header lines come first, before the title block
    assert lines[0].startswith("Model: ")
    assert lines[0].split(": ")[1] in dir_ai.SUPPORTED_AI_MODELS
    assert any(l.startswith("Meta Title: ") for l in lines[:4])
    assert any(l.startswith("Meta Description: ") for l in lines[:4])
    # the Image line points at the documented by-name path for this content id
    assert f"{dir_ai.DATA_BASE}/{name}/{name}.png" in txt
    # required sections, in order
    assert txt.index("Summary") < txt.index("Details") < txt.index("At a glance")
    # Details opens with the question, verbatim
    details = txt.split("Details", 1)[1].strip()
    assert details.startswith(p["conversation"][0]["text"])
    assert "<" not in txt, "plain text only - never HTML"


def test_ai_model_is_a_supported_lowercase_style_key():
    assert _payload(model="gemini")["ai_model"] == "gemini"
    assert _payload(model="chatgpt")["ai_model"] == "chatgpt"
    # perplexity is not a supported style key; it must fall back, not be sent as-is
    assert _payload(model="perplexity")["ai_model"] in dir_ai.SUPPORTED_AI_MODELS


def test_image_is_only_set_when_actually_hosted():
    assert "image" not in _payload()
    p = _payload(image_url="https://myqsd.com/dir-ai-data/x/x.png")
    assert p["image"] == "https://myqsd.com/dir-ai-data/x/x.png"


def test_published_urls_merge_never_loses_a_live_url(tmp_path: Path):
    """A later batch must not erase URLs an earlier batch already earned."""
    p = tmp_path / "published_urls.csv"
    dir_ai.write_published_urls([
        {"query_id": "q1", "model": "ChatGPT", "public_url": "https://live/one",
         "safe_to_share": "yes", "screenshot_path": "/1.png", "answer_path": "/1.txt"}], p)
    # second batch: a different row, plus a URL-less retry of the first
    dir_ai.write_published_urls([
        {"query_id": "q1", "model": "ChatGPT", "public_url": "",
         "safe_to_share": "yes", "screenshot_path": "/1.png", "answer_path": "/1.txt"},
        {"query_id": "q2", "model": "Gemini", "public_url": "https://live/two",
         "safe_to_share": "yes", "screenshot_path": "/2.png", "answer_path": "/2.txt"}], p)
    import csv as _csv
    with p.open(encoding="utf-8-sig") as fh:
        rows = {(r["query_id"], r["model"]): r["public_url"] for r in _csv.DictReader(fh)}
    assert rows[("q1", "ChatGPT")] == "https://live/one", "existing live URL was clobbered"
    assert rows[("q2", "Gemini")] == "https://live/two"


# --- published output must never leak local paths ----------------------------

def test_local_screenshot_path_is_never_published():
    """metadata renders on the live page - a local path there leaks our layout."""
    p = _payload(screenshot_path=r"C:\git\AI_Mention-service\inputs\shots\q1.png")
    blob = json.dumps(p)
    assert "C:" not in blob and "AI_Mention-service" not in blob
    assert "screenshot_path" not in p["metadata"]


def test_screenshot_url_only_appears_when_actually_hosted():
    assert "screenshot_url" not in _payload()["metadata"]
    p = _payload(image_url="https://cdn.example/q1.png")
    assert p["metadata"]["screenshot_url"] == "https://cdn.example/q1.png"
    assert p["image"] == "https://cdn.example/q1.png"
