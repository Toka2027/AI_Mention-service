"""Capture orchestration. Writes prompt packets always; runs the browser capturer
only when not --prepare-only. Playwright is imported lazily inside the loop so this
module (and `--prepare-only`) works without it installed.
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
    headful: bool,
    login_wait: bool,
    resume: bool,
    prepare_only: bool,
) -> int:
    ci = ClientInput.from_json(input_path)
    slug = ci.client_slug or pages.slugify(ci.brand)
    oid = pages.slugify(order_id or ci.order_id or "order-001")
    inputs_root = Path(input_path).resolve().parent
    caps = Path(captures_dir) if captures_dir else inputs_root / "captures" / slug / oid
    shots = Path(shots_dir) if shots_dir else inputs_root / "screenshots" / slug / oid

    qs = generator.generate_questions(ci, ci.pkg.n_questions)
    qmap = {q.id: q for q in qs}
    qids = _parse_range(questions_range, len(qs))
    sel_models = [m.lower() for m in models] or [m.lower() for m in ci.pkg.models]

    written = ingest.write_prompt_packet(ci, qs, caps)
    print(f"Prompt packet: {written} prompt files under {caps}")
    print(f"Models: {sel_models}  |  questions: {qids[0]}-{qids[-1]}  |  screenshots -> {shots}")

    if prepare_only:
        print("prepare-only: no browser launched. Prompts are ready for capture.")
        return 0

    try:
        from .browser import PlaywrightCapturer  # lazy: needs playwright
    except Exception as exc:  # noqa: BLE001
        print("ERROR: Playwright is not available. Install it in the operator environment:")
        print("  pip install playwright && playwright install chromium")
        print(f"  ({exc})")
        return 1

    shots.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    for model in sel_models:
        mdir = caps / model
        mdir.mkdir(parents=True, exist_ok=True)
        with (mdir / "evidence.jsonl").open("a", encoding="utf-8") as log:
            try:
                with PlaywrightCapturer(model, headful=headful, login_wait=login_wait) as cap:
                    for qid in qids:
                        ans_file = mdir / f"q{qid}.txt"
                        shot = shots / f"q{qid}_{model}.png"
                        if resume and ans_file.exists() and shot.exists():
                            continue
                        res = cap.capture(qid, qmap[qid].text, shot)
                        if res.ok and res.answer:
                            ans_file.write_text(res.answer, encoding="utf-8")
                            (mdir / f"q{qid}.evidence.txt").write_text("browser", encoding="utf-8")
                            if res.urls:
                                (mdir / f"q{qid}.urls.txt").write_text("\n".join(res.urls), encoding="utf-8")
                            ok += 1
                        else:
                            fail += 1
                        log.write(json.dumps({"model": model, "q": qid, "ok": res.ok, "notes": res.notes}) + "\n")
            except Exception as exc:  # noqa: BLE001
                print(f"[{model}] session error: {exc!r}")
    print(f"Capture done. ok={ok} fail={fail}. Next: run `deliver` to regenerate + strict QA.")
    return 0 if fail == 0 else 1
