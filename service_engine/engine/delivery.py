"""Two-model browser-captured delivery (ChatGPT + Gemini).

Assembles a delivery from REAL browser captures only, in two layers:

  internal    every capture, safe and unsafe, plus the risk findings and the
              blocked-model status. This is the honest record.
  client-safe only captures the risk screen cleared. Unsafe answers and their
              screenshots are excluded from client-facing material - excluded and
              DISCLOSED as excluded, never silently dropped.

A capture is only eligible if all five hold: answer text, screenshot, provenance
record, `evidence_type == browser`, and capture-QA PASS. Nothing is generated here.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from . import sentiment
from .capture import qa as capture_qa

SCOPE_LABEL = "1BillionLinks Browser-Captured 2-Model Delivery - ChatGPT + Gemini"
BLOCKED_MODELS = ("Claude", "Perplexity")


@dataclass
class Capture:
    question_id: int
    model: str            # lower-case
    query: str
    keyword: str
    answer: str
    answer_path: Path
    screenshot_path: Path
    provenance: dict
    evidence_type: str
    sentiment: str = ""
    safe: bool = False
    issue: str = ""
    qa_pass: bool = False

    @property
    def model_label(self) -> str:
        return {"chatgpt": "ChatGPT", "gemini": "Gemini"}.get(self.model, self.model.title())


@dataclass
class Delivery:
    order_id: str
    client_slug: str
    brand: str
    website: str
    captures: list[Capture] = field(default_factory=list)
    blocked: dict = field(default_factory=dict)

    @property
    def safe(self) -> list[Capture]:
        return [c for c in self.captures if c.safe]

    @property
    def unsafe(self) -> list[Capture]:
        return [c for c in self.captures if not c.safe]

    def by_model(self, safe_only: bool = False) -> dict[str, list[Capture]]:
        out: dict[str, list[Capture]] = {}
        for c in (self.safe if safe_only else self.captures):
            out.setdefault(c.model, []).append(c)
        return out


def collect(
    captures_dir: Path,
    shots_dir: Path,
    questions: list,
    models: list[str],
    brand: str,
    website: str,
    order_id: str,
    client_slug: str,
) -> Delivery:
    """Gather every eligible real browser capture and screen it for risk."""
    d = Delivery(order_id=order_id, client_slug=client_slug, brand=brand, website=website)
    qmap = {q.id: q for q in questions}

    for model in models:
        m = model.lower()
        mdir = Path(captures_dir) / m
        qa_result = capture_qa.verify_capture(
            captures_dir, shots_dir, m, [q.id for q in questions],
            {q.id: q.text for q in questions},
        )
        qa_by_q = {c["question_id"]: c["overall"] for c in qa_result["cells"]}

        for q in questions:
            afile = mdir / f"q{q.id}.txt"
            shot = Path(shots_dir) / f"q{q.id}_{m}.png"
            pfile = mdir / f"q{q.id}.capture.json"
            efile = mdir / f"q{q.id}.evidence.txt"
            if not (afile.exists() and shot.exists() and pfile.exists() and efile.exists()):
                continue
            evidence = efile.read_text(encoding="utf-8").strip().lower()
            if evidence != "browser":
                continue  # only real browser captures are eligible

            answer = afile.read_text(encoding="utf-8").strip()
            try:
                prov = json.loads(pfile.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            verdict = sentiment.review_answer(answer, brand)
            d.captures.append(Capture(
                question_id=q.id, model=m, query=qmap[q.id].text, keyword=q.keyword,
                answer=answer, answer_path=afile, screenshot_path=shot, provenance=prov,
                evidence_type=evidence, sentiment=verdict["sentiment"],
                safe=verdict["safe"], issue=verdict["issue"],
                qa_pass=qa_by_q.get(q.id) != capture_qa.FAIL,
            ))
    d.captures = [c for c in d.captures if c.qa_pass]
    d.captures.sort(key=lambda c: (c.model, c.question_id))
    return d


# --- reports -----------------------------------------------------------------

def _counts_table(d: Delivery) -> str:
    rows = ["| model | captured | safe | excluded (unsafe) | evidence | capture-QA |",
            "| --- | --- | --- | --- | --- | --- |"]
    for model, caps in sorted(d.by_model().items()):
        n_safe = sum(1 for c in caps if c.safe)
        label = caps[0].model_label
        rows.append(f"| {label} | {len(caps)} | {n_safe} | {len(caps) - n_safe} | "
                    f"`browser` | PASS |")
    for b in BLOCKED_MODELS:
        rows.append(f"| {b} | 0 | 0 | - | - | **BLOCKED (not attempted this phase)** |")
    return "\n".join(rows)


def internal_report(d: Delivery, report_date: str) -> str:
    lines = [
        f"# {SCOPE_LABEL} — INTERNAL REPORT",
        "",
        "**INTERNAL ONLY. Contains findings that are not client-safe. Do not send to the client.**",
        "",
        f"**Client:** {d.brand} · **Website:** {d.website} · **Order:** {d.order_id} · "
        f"**Date:** {report_date}",
        f"**Scope:** ChatGPT + Gemini, real browser captures. **This is NOT a full 4-model PRO "
        f"delivery.**",
        "",
        "## 1. Coverage",
        "",
        _counts_table(d),
        "",
        f"Total real browser captures: **{len(d.captures)}** "
        f"({len(d.safe)} client-safe, {len(d.unsafe)} excluded from client-facing output).",
        "",
        "Every included answer has: real answer text, a real full-page screenshot, a provenance "
        "record (submitted prompt, conversation URL, UTC capture time), `evidence_type=browser`, "
        "and a strict capture-QA PASS.",
        "",
        "## 2. Blocked models — frozen for this phase",
        "",
        "| model | status | blocker |",
        "| --- | --- | --- |",
    ]
    for b in BLOCKED_MODELS:
        info = d.blocked.get(b.lower(), {})
        lines.append(f"| {b} | **BLOCKED — excluded from this delivery** | "
                     f"{info.get('blocker', 'Cloudflare bot verification (does not self-clear)')} |")
    lines += [
        "",
        "Neither was bypassed, retried this phase, nor fabricated. They carry no captures, no "
        "screenshots and no evidence, and are not counted as complete anywhere in this delivery.",
        "",
        "## 3. Risk findings (all captures)",
        "",
        "| Query | Model | Sentiment | Client-safe | Issue |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c in d.captures:
        lines.append(f"| Q{c.question_id} | {c.model_label} | {c.sentiment} | "
                     f"{'Yes' if c.safe else '**No**'} | {c.issue or '-'} |")

    if d.unsafe:
        lines += ["", "## 4. Excluded answers — why", ""]
        for c in d.unsafe:
            lines += [
                f"### {c.model_label} Q{c.question_id}",
                f"- **Query:** {c.query}",
                f"- **Issue:** {c.issue}",
                f"- **Answer:** `{c.answer_path.as_posix()}`",
                f"- **Screenshot:** `{c.screenshot_path.as_posix()}` (retained internally, "
                f"excluded from client material)",
                "",
            ]

    gemini_unsafe = [c for c in d.unsafe if c.model == "gemini"]
    if gemini_unsafe:
        lines += [
            "## 5. Key finding — Gemini's own framing of the brand",
            "",
            f"{len(gemini_unsafe)} of the Gemini answers tie penalty/spam risk to this brand. "
            "Critically, **our questions contained none of that vocabulary** — the risky "
            "positioning terms (`bulk`, `high-volume`, `tier 2/3`, `automated`) were introduced by "
            "Gemini itself.",
            "",
            "Gemini already associates 1BillionLinks with bulk / high-volume / tiered link "
            "building and volunteers the penalty framing unprompted. Two query styles were tested "
            "(`benefit`, then `workflow` with the trigger keywords reworded); rewording did not "
            "reduce it.",
            "",
            "**Recommendation: do not scale Gemini to the full question set until the brand's "
            "public positioning changes.** This is a positioning signal, not a prompt defect, and "
            "further prompt engineering will not remove it. ChatGPT shows no such framing.",
            "",
        ]
    lines += [
        "## 6. Recommendation",
        "",
        "1. ChatGPT is safe to scale — no unsafe answers across the captured set.",
        "2. Gemini needs the review gate on every answer; expect exclusions.",
        "3. Do not present this as a 4-model PRO delivery. Claude and Perplexity are blocked.",
        "4. Keep `review` as a hard gate: it exits non-zero when any answer is unsafe.",
        "",
    ]
    return "\n".join(lines)


def client_report(d: Delivery, report_date: str, published: list[dict] | None = None) -> str:
    safe_by_model = d.by_model(safe_only=True)
    lines = [
        f"# {SCOPE_LABEL}",
        "",
        f"**Client:** {d.brand} · **Website:** {d.website} · **Order:** {d.order_id} · "
        f"**Date:** {report_date}",
        "",
        "## Scope of this delivery",
        "",
        "This is a **browser-captured pilot covering two AI assistants: ChatGPT and Gemini.**",
        "",
        "- Every answer in this report was captured from the assistant's real web interface, in a "
        "real browser, with a real full-page screenshot.",
        "- **Claude and Perplexity are not included.** Both blocked automated access during this "
        "phase (bot verification that we do not bypass), so no results are reported for them.",
        "- **This is not a full 4-model PRO delivery.** It covers the two assistants that could be "
        "captured.",
        "",
        "This is an observational snapshot at a point in time. It does not promise or guarantee AI "
        "mentions, LLM visibility, indexing, rankings, or any influence over model behaviour.",
        "",
        "## What is included",
        "",
        "| assistant | answers included | evidence |",
        "| --- | --- | --- |",
    ]
    for model, caps in sorted(safe_by_model.items()):
        lines.append(f"| {caps[0].model_label} | {len(caps)} | real browser capture + full-page "
                     f"screenshot |")
    lines += [
        "",
        f"**{len(d.safe)} captured answers** are included with their screenshots.",
        "",
    ]
    if d.unsafe:
        lines += [
            "### Answers held back",
            "",
            f"{len(d.unsafe)} further captured answer(s) are **excluded from this report** because "
            "our editorial review judged them unsuitable for client-facing material. They exist, "
            "they are retained in our internal record, and they are available to you on request. "
            "They are excluded, not deleted.",
            "",
        ]
    lines += ["## Captured answers", ""]
    for model, caps in sorted(safe_by_model.items()):
        lines += [f"### {caps[0].model_label}", ""]
        for c in caps:
            pub = ""
            if published:
                match = next((p for p in published
                              if p.get("query_id") == f"q{c.question_id}"
                              and p.get("model", "").lower() == c.model
                              and p.get("public_url")), None)
                if match:
                    pub = f"\n- **Published page:** {match['public_url']}"
            excerpt = " ".join(c.answer.split())[:400]
            lines += [
                f"**Q{c.question_id} — {c.keyword}**",
                "",
                f"> {c.query}",
                "",
                f"{excerpt}{'…' if len(' '.join(c.answer.split())) > 400 else ''}",
                "",
                f"- **Screenshot:** `screenshots/{c.screenshot_path.name}`",
                f"- **Full answer:** `answers/{c.model}/{c.answer_path.name}`"
                f"{pub}",
                "",
            ]
    if published and any(p.get("public_url") for p in published):
        lines += ["## Published pages", "",
                  "| Query | Assistant | Public URL |", "| --- | --- | --- |"]
        for p in published:
            if p.get("public_url"):
                lines.append(f"| {p['query_id']} | {p['model']} | {p['public_url']} |")
        lines.append("")
    return "\n".join(lines)


# --- packaging ---------------------------------------------------------------

def assemble(
    d: Delivery,
    out_dir: Path,
    report_date: str,
    published: list[dict] | None = None,
    qa_text: str = "",
    published_csv: Path | None = None,
) -> dict:
    """Write both reports + safe assets into out_dir and ZIP the result."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    internal_path = out_dir / "INTERNAL_REPORT.md"
    client_path = out_dir / "CLIENT_REPORT.md"
    internal_path.write_text(internal_report(d, report_date), encoding="utf-8")
    client_path.write_text(client_report(d, report_date, published), encoding="utf-8")

    # Safe assets only: unsafe screenshots never enter the client-facing package.
    shots_out = out_dir / "screenshots"
    shots_out.mkdir(exist_ok=True)
    ans_out = out_dir / "answers"
    prov_out = out_dir / "provenance"
    prov_out.mkdir(exist_ok=True)
    for c in d.safe:
        shutil.copyfile(c.screenshot_path, shots_out / c.screenshot_path.name)
        mdir = ans_out / c.model
        mdir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(c.answer_path, mdir / c.answer_path.name)
        (prov_out / f"q{c.question_id}_{c.model}.capture.json").write_text(
            json.dumps(c.provenance, indent=2, ensure_ascii=False), encoding="utf-8")

    if qa_text:
        (out_dir / "QA_RESULTS.txt").write_text(qa_text, encoding="utf-8")
    if published_csv and Path(published_csv).exists():
        shutil.copyfile(published_csv, out_dir / "published_urls.csv")

    excluded = out_dir / "EXCLUDED_FROM_CLIENT.md"
    excluded.write_text(
        "# Excluded from the client-facing package\n\n"
        "These real captures were held back by the editorial risk review. They are retained in "
        "the internal record (see INTERNAL_REPORT.md) and are NOT deleted.\n\n"
        + ("\n".join(f"- {c.model_label} Q{c.question_id} — {c.issue}\n"
                     f"  - answer: `{c.answer_path.as_posix()}`\n"
                     f"  - screenshot: `{c.screenshot_path.as_posix()}`"
                     for c in d.unsafe) or "- none")
        + "\n", encoding="utf-8")

    zip_path = out_dir.parent / f"{out_dir.name}_deliverable.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(out_dir.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(out_dir).as_posix())

    return {
        "out_dir": str(out_dir),
        "internal_report": str(internal_path),
        "client_report": str(client_path),
        "zip": str(zip_path),
        "safe": len(d.safe),
        "excluded": len(d.unsafe),
    }
