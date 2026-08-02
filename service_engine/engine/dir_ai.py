"""Directory Article API publishing (myqsd.com).

Turns real browser captures into publishable article pages and POSTs them to the
Directory Article API using an inline JSON payload (no separate content-file upload).

Endpoint : POST https://myqsd.com/api/dir-ai-order.php
Auth     : header `X-Dir-Ai-Api-Key`, value read from the DIR_AI_API_KEY environment
           variable. The key is NEVER read from a file in the repo, never logged, and
           never written into a payload or manifest.

Screenshots: this module does NOT upload images. The API contract we were given
describes an article payload only, so a screenshot is referenced by its LOCAL path in
`metadata.screenshot_path` for traceability, and the publish-ready folder lists the
files that still need hosting before any public image URL can be claimed.
"""

from __future__ import annotations

import csv
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

API_ENDPOINT = "https://myqsd.com/api/dir-ai-order.php"
API_KEY_ENV = "DIR_AI_API_KEY"
API_KEY_HEADER = "X-Dir-Ai-Api-Key"

MODEL_LABELS = {"chatgpt": "ChatGPT", "gemini": "Gemini",
                "claude": "Claude", "perplexity": "Perplexity"}

# Page-style keys the API accepts for `ai_model` (lower-case). Perplexity is not one
# of them, so a Perplexity capture would fall back to the default style.
SUPPORTED_AI_MODELS = ("chatgpt", "gemini", "claude", "grok")


def api_key() -> str | None:
    """The API key from the environment, or None when it is not configured."""
    key = (os.environ.get(API_KEY_ENV) or "").strip()
    return key or None


_UI_LABEL = re.compile(r"^\s*(ChatGPT|Gemini|Claude|Perplexity)\s+said:\s*", re.IGNORECASE)


def strip_ui_chrome(answer: str) -> str:
    """Remove the chat UI's own speaker label from the front of a captured answer.

    Signed-out ChatGPT renders the assistant turn with a visible "ChatGPT said:"
    heading, which the DOM extraction picks up. That label is interface furniture, not
    part of the model's reply, so it is removed for PUBLISHED pages. The stored
    evidence file is never modified - it stays byte-for-byte as captured, so the
    screenshot and the answer file continue to correspond exactly.
    """
    return _UI_LABEL.sub("", answer or "", count=1).lstrip()


def _summary(answer: str, limit: int = 320) -> str:
    """First sentences of the captured answer, trimmed to a clean boundary."""
    text = " ".join((answer or "").split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    stop = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[:stop + 1] if stop > 120 else cut.rsplit(" ", 1)[0]) + ""


def build_payload(
    *,
    brand: str,
    website: str,
    model: str,
    question_id: int,
    query: str,
    answer: str,
    order_id: str,
    evidence_type: str,
    screenshot_path: str,   # local path - retained for internal records, NEVER published
    capture_time: str,
    client_safe: bool,
    keyword: str = "",
    image_url: str = "",
) -> dict:
    """One Directory Article payload for one captured answer.

    `conversation` carries the EXACT submitted query and the EXACT captured answer -
    neither is edited, trimmed, or rewritten anywhere in this module.
    """
    label = MODEL_LABELS.get(model.lower(), model)
    topic = keyword or "SEO link building"
    answer = strip_ui_chrome(answer)
    # `ai_model` must be one of the API's supported style keys, lower-case. It selects
    # the page style only and is not rendered as a brand name.
    style = model.lower() if model.lower() in SUPPORTED_AI_MODELS else "chatgpt"
    title = f"{brand} and {topic}: what {label} says"
    payload = {
        "title": title,
        "subtitle": f"Real {label} answer captured in-browser for {brand}",
        "ai_model": style,
        "summary": _summary(answer),
        "meta_title": title[:70],
        "meta_description": _summary(answer, 155),
        # The live API contract (GET the endpoint for its self-description) uses
        # "text" for message bodies, NOT "content". `content` is also emitted for
        # forward-compatibility; the renderer reads `text`.
        "conversation": [
            {"role": "user", "text": query, "content": query},
            {"role": "assistant", "text": answer, "content": answer},
        ],
        "metadata": {
            "brand": brand,
            "website": website,
            "model": label,
            "query_id": f"q{question_id}",
            "order_id": order_id,
            "evidence_type": evidence_type,
            # PUBLIC URL ONLY. `metadata` is rendered on the live page, so a local
            # filesystem path here leaks our internal directory layout to every
            # visitor. Local paths stay in the delivery ZIP and provenance files,
            # never in a published payload.
            "screenshot_url": image_url or "",
            "capture_time": capture_time,
            "client_safe": client_safe,
        },
    }
    if not image_url:
        payload["metadata"].pop("screenshot_url")
    # `image` must be an ABSOLUTE public URL. It is only set when the screenshot has
    # actually been hosted - never invented from a local path.
    if image_url:
        payload["image"] = image_url
    return payload


def post_article(payload: dict, endpoint: str = API_ENDPOINT, timeout: int = 45) -> dict:
    """POST one article. Returns {ok, status, url, raw, error}. Never raises."""
    key = api_key()
    if not key:
        return {"ok": False, "status": 0, "url": "", "raw": "",
                "error": f"{API_KEY_ENV} is not set in the environment"}

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=data, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8",
                 "Accept": "application/json", API_KEY_HEADER: key},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return {"ok": False, "status": exc.code, "url": "", "raw": body[:1500],
                "error": f"HTTP {exc.code}: {exc.reason}"}
    except Exception as exc:  # noqa: BLE001 - network/DNS/TLS
        return {"ok": False, "status": 0, "url": "", "raw": "",
                "error": f"{type(exc).__name__}: {exc}"}

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {"ok": 200 <= status < 300, "status": status, "url": "",
                "raw": body[:1500], "error": "" if 200 <= status < 300 else "non-JSON response"}

    # The documented success response is {"link": ..., "tenant": ..., "token": ...}.
    url = ""
    for k in ("link", "url", "public_url", "permalink", "article_url"):
        if isinstance(parsed.get(k), str) and parsed[k].startswith("http"):
            url = parsed[k]
            break
    if not url and isinstance(parsed.get("data"), dict):
        for k in ("url", "public_url", "link", "permalink"):
            v = parsed["data"].get(k)
            if isinstance(v, str) and v.startswith("http"):
                url = v
                break
    ok = (200 <= status < 300) and parsed.get("success", True) is not False
    return {"ok": ok, "status": status, "url": url, "raw": body[:1500],
            "error": "" if ok else str(parsed.get("error") or parsed.get("message") or "")}


DATA_BASE = "https://myqsd.com/dir-ai-data"


def content_name(client_slug: str, question_id: int, model: str) -> str:
    """Short content id for the by-name route. Allowed chars: letters, digits, . - _"""
    return f"{client_slug}-q{question_id}-{model.lower()}"


def build_txt_file(payload: dict, name: str, capture_date: str = "") -> str:
    """Render the documented plain-text content format for the by-name route.

    Layout (from the API guide): optional header lines, then the title block, then
    `Summary`, `Details` (first paragraph = the question, rest = the answer), then an
    optional `At a glance` label/value block. Plain text only - never HTML.

    The `Image:` line points at the path where the screenshot WILL live once uploaded
    to the data folder. It resolves only after upload; nothing here asserts that the
    upload has happened.
    """
    md = payload.get("metadata", {})
    question = payload["conversation"][0]["text"]
    answer = payload["conversation"][1]["text"]
    lines = [
        f"Model: {payload.get('ai_model', 'chatgpt')}",
        f"Meta Title: {payload.get('meta_title', payload['title'])}",
        f"Meta Description: {payload.get('meta_description', '')}",
        f"Image: {DATA_BASE}/{name}/{name}.png",
        "",
        payload["title"],
        payload.get("subtitle", ""),
        "",
        "Summary",
        "",
        payload.get("summary", ""),
        "",
        "Details",
        "",
        question,
        "",
    ]
    for para in [p.strip() for p in answer.split("\n") if p.strip()]:
        lines += [para, ""]
    lines += [
        "At a glance",
        "",
        f"Brand {md.get('brand', '')}",
        f"Assistant {md.get('model', '')}",
        f"Captured {capture_date or md.get('capture_time', '')}",
        f"Evidence {md.get('evidence_type', '')}",
        "",
    ]
    return "\n".join(lines)


VERIFY_COLS = ["query_id", "model", "public_url", "http_status", "has_question",
               "has_answer", "has_image", "image_url", "verified_at", "notes"]


def verify_published_page(url: str, question: str, answer: str,
                          expected_image: str = "", timeout: int = 40) -> dict:
    """Fetch a live page and check what is actually rendered on it.

    Conservative by design: a page only counts as carrying its screenshot when the
    exact expected image URL appears in the HTML. It also fails the page if a local
    filesystem path or an API key leaked into the published output.
    """
    import html as _html
    import re as _re
    import urllib.error
    import urllib.request
    from datetime import datetime, timezone

    row = {"public_url": url, "http_status": 0, "has_question": False,
           "has_answer": False, "has_image": False, "image_url": "",
           "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "notes": ""}
    notes: list[str] = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", errors="replace")
            row["http_status"] = r.status
    except urllib.error.HTTPError as exc:
        row["http_status"] = exc.code
        row["notes"] = f"HTTP {exc.code}"
        return row
    except Exception as exc:  # noqa: BLE001
        row["notes"] = f"{type(exc).__name__}"
        return row

    stripped = _re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=_re.S)
    text = _re.sub(r"\s+", " ", _html.unescape(_re.sub(r"<[^>]+>", " ", stripped))).strip()

    def _probe(sample: str, n: int = 60) -> bool:
        s = " ".join((sample or "").split())[:n]
        return bool(s) and s in text

    row["has_question"] = _probe(question)
    row["has_answer"] = _probe(strip_ui_chrome(answer))
    if expected_image:
        row["has_image"] = expected_image in raw
        row["image_url"] = expected_image if row["has_image"] else ""
        if not row["has_image"]:
            notes.append("expected image URL not present on page")
    else:
        notes.append("no image URL expected for this page")

    # Leak checks - these must never appear in published output.
    if _re.search(r"[A-Za-z]:[\\/](?:git|Users)[\\/]", raw):
        notes.append("LEAK: local filesystem path on page")
    key = api_key()
    if key and key in raw:
        notes.append("LEAK: API key on page")
    if not row["has_question"]:
        notes.append("question text not found")
    if not row["has_answer"]:
        notes.append("answer text not found")

    row["notes"] = "; ".join(notes) if notes else "ok"
    return row


def write_verification_csv(rows: list[dict], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=VERIFY_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in VERIFY_COLS})
    return p


PUBLISHED_COLS = ["query_id", "model", "public_url", "safe_to_share",
                  "screenshot_path", "answer_path"]


def write_published_urls(rows: list[dict], path: str | Path, merge: bool = True) -> Path:
    """Write the published-URL table, MERGING with any existing file by default.

    Publishing often runs in batches (one model, or a retry of failures). Without
    merging, a later batch would overwrite the URLs an earlier batch already earned -
    silently losing live links. Existing rows are kept unless the new batch actually
    carries a URL for the same (query_id, model).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    merged: dict[tuple[str, str], dict] = {}
    if merge and p.exists():
        with p.open("r", encoding="utf-8-sig", newline="") as fh:
            for old in csv.DictReader(fh):
                merged[(old.get("query_id", ""), old.get("model", ""))] = dict(old)
    for r in rows:
        k = (r.get("query_id", ""), r.get("model", ""))
        prev = merged.get(k)
        # never let a URL-less retry clobber a URL we already hold
        if prev and prev.get("public_url") and not r.get("public_url"):
            prev.update({c: r.get(c, prev.get(c, "")) for c in PUBLISHED_COLS
                         if c != "public_url"})
        else:
            merged[k] = r

    def _sort_key(item):
        (qid, model), _ = item
        num = int("".join(ch for ch in qid if ch.isdigit()) or 0)
        return (model, num)

    rows = [v for _, v in sorted(merged.items(), key=_sort_key)]
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PUBLISHED_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in PUBLISHED_COLS})
    return p
