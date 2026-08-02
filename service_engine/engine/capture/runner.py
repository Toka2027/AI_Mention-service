"""Capture orchestration.

Writes the prompt packet always; runs the real browser capturer unless
--prepare-only. Playwright is imported lazily so `--prepare-only` still works in an
environment without it.

Every successful capture writes four files into the drop-folder, which together are
the proof that the answer came from a real LLM UI:
    q{id}.txt           the real answer text
    q{id}.evidence.txt  the literal string "browser"
    q{id}.capture.json  provenance (submitted prompt, page URL, UTC time, shot size)
    q{id}.urls.txt      URLs found in the answer (only when there are any)
plus the real full-page screenshot at  <shots>/q{id}_{model}.png
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import generator, ingest, pages
from ..models import ClientInput


def _parse_range(spec: str | None, n: int) -> list[int]:
    if not spec:
        return list(range(1, n + 1))
    ids: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            ids.update(range(int(a), int(b) + 1))
        elif part:
            ids.add(int(part))
    return sorted(i for i in ids if 1 <= i <= n)


def run_capture(
    input_path: str,
    order_id: str | None,
    models: list[str],
    captures_dir: str | None,
    shots_dir: str | None,
    questions_range: str | None,
    headful: bool = True,
    login_wait: bool = False,
    resume: bool = False,
    prepare_only: bool = False,
    smoke: bool = False,
    confirm_each: bool = False,
    answer_timeout_s: int = 180,
    new_chat_each: bool = True,
    cdp_endpoint: str | None = None,
) -> int:
    ci = ClientInput.from_json(input_path)
    slug = ci.client_slug or pages.slugify(ci.brand)
    oid = pages.slugify(order_id or ci.order_id or "order-001")
    inputs_root = Path(input_path).resolve().parent
    caps = Path(captures_dir) if captures_dir else inputs_root / "captures" / slug / oid
    shots = Path(shots_dir) if shots_dir else inputs_root / "screenshots" / slug / oid

    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    qmap = {q.id: q for q in qs}
    sel_models = [m.lower() for m in models] or [m.lower() for m in ci.pkg.models]
    qids = _parse_range(questions_range, len(qs))

    if smoke:  # prove the flow end-to-end: exactly one model, exactly one question
        sel_models = sel_models[:1]
        qids = qids[:1]

    written = ingest.write_prompt_packet(ci, qs, caps)
    print(f"Prompt packet: {written} prompt files under {caps}")
    print(f"{'SMOKE TEST  ' if smoke else ''}Models: {sel_models}  |  "
          f"questions: {qids}  |  screenshots -> {shots}")

    if prepare_only:
        print("prepare-only: no browser launched. Prompts are ready for capture.")
        return 0

    try:
        from .browser import PlaywrightCapturer  # lazy: needs playwright
    except Exception as exc:  # noqa: BLE001
        print("ERROR: Playwright is not available. Install it in the operator environment:")
        print("  python -m pip install -r requirements-capture.txt")
        print("  python -m playwright install chromium")
        print(f"  ({exc})")
        return 1

    shots.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    for model in sel_models:
        mdir = caps / model
        mdir.mkdir(parents=True, exist_ok=True)
        with (mdir / "evidence.jsonl").open("a", encoding="utf-8") as log:
            try:
                with PlaywrightCapturer(
                    model, headful=headful, login_wait=login_wait,
                    answer_timeout_s=answer_timeout_s, confirm_each=confirm_each,
                    cdp_endpoint=cdp_endpoint,
                ) as cap:
                    for n, qid in enumerate(qids):
                        ans_file = mdir / f"q{qid}.txt"
                        shot = shots / f"q{qid}_{model}.png"
                        if resume and ans_file.exists() and shot.exists():
                            print(f"[{model} q{qid}] already captured - skipped (--resume)")
                            continue
                        # Start a clean conversation before EVERY question, including the
                        # first. In CDP mode we attach to whatever tab the operator left
                        # open, which may already hold an unrelated thread - that would
                        # put someone else's exchange in our evidence screenshot.
                        if new_chat_each:
                            cap.new_chat()
                        print(f"[{model} q{qid}] submitting: {qmap[qid].text[:70]}...")
                        res = cap.capture(qid, qmap[qid].text, shot)

                        if res.ok and res.answer:
                            ans_file.write_text(res.answer, encoding="utf-8")
                            (mdir / f"q{qid}.evidence.txt").write_text("browser", encoding="utf-8")
                            (mdir / f"q{qid}.capture.json").write_text(
                                json.dumps(res.provenance(), indent=2, ensure_ascii=False),
                                encoding="utf-8",
                            )
                            if res.urls:
                                (mdir / f"q{qid}.urls.txt").write_text(
                                    "\n".join(res.urls), encoding="utf-8")
                            ok += 1
                            print(f"[{model} q{qid}] OK  answer={len(res.answer)} chars  "
                                  f"shot={res.screenshot_width}x{res.screenshot_height} "
                                  f"({res.screenshot_bytes} bytes)")
                        else:
                            fail += 1
                            print(f"[{model} q{qid}] FAILED: {res.notes}")
                        log.write(json.dumps(
                            {"model": model, "q": qid, "ok": res.ok, "notes": res.notes,
                             "captured_at": res.captured_at}) + "\n")
            except Exception as exc:  # noqa: BLE001
                print(f"[{model}] session error: {exc}")
                fail += 1

    print(f"\nCapture done. ok={ok} fail={fail}")
    if ok:
        print(f"  answers     -> {caps}/<model>/q<id>.txt")
        print(f"  screenshots -> {shots}/q<id>_<model>.png")
        print("  next: capture-qa (verify this capture), then deliver (regenerate + strict QA)")
    return 0 if fail == 0 and ok > 0 else 1
