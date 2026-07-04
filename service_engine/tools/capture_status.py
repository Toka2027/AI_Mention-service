"""Capture-progress helper (pre-run checklist) for a manual multi-model order.

Reports, per model: how many answers are filled in the responses CSV and how many
REAL browser screenshots are present in the persistent input folder, plus the exact
missing filenames. Use it before re-running the engine to see what's left.

Does NOT touch any LLM. Read-only. Run from service_engine/:

    python tools/capture_status.py
    python tools/capture_status.py --responses inputs/1billionlinks_responses.csv \
        --shots-dir inputs/screenshots/1billionlinks/2026-06-28-001 --proof-ok-models Claude
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

PENDING = "[pending capture]"


def main() -> int:
    ap = argparse.ArgumentParser(description="Manual capture progress + screenshot naming helper.")
    ap.add_argument("--responses", default="inputs/1billionlinks_responses.csv")
    ap.add_argument("--shots-dir", default="inputs/screenshots/1billionlinks/2026-06-28-001")
    ap.add_argument("--proof-ok-models", default="Claude",
                    help="Comma list of models that may use an engine proof card (no real screenshot needed).")
    args = ap.parse_args()

    resp = Path(args.responses)
    shots = Path(args.shots_dir)
    proof_ok = {m.strip().lower() for m in args.proof_ok_models.split(",") if m.strip()}

    if not resp.exists():
        print(f"ERROR: responses file not found: {resp}")
        return 1

    rows = list(csv.DictReader(resp.open(encoding="utf-8-sig")))
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)

    print(f"Capture status  |  responses: {resp}")
    print(f"                |  screenshots input: {shots}{'  (missing)' if not shots.exists() else ''}")
    print(f"                |  proof-ok models (no real screenshot needed): {sorted(proof_ok) or 'none'}")
    print("-" * 72)

    all_ready = True
    for model in sorted(by_model):
        mrows = by_model[model]
        total = len(mrows)
        answered_ids, missing_answers = [], []
        for r in mrows:
            qid = r["question_id"]
            if (r.get("answer") or "").strip() not in ("", PENDING):
                answered_ids.append(qid)
            else:
                missing_answers.append(qid)
        # real screenshots present in the input dir
        needs_real = model.lower() not in proof_ok
        present_shot, missing_shot = [], []
        for r in mrows:
            qid = r["question_id"]
            stem = f"q{qid}_{model.lower()}"
            has = bool(list(shots.glob(stem + "*.png"))) if shots.exists() else False
            (present_shot if has else missing_shot).append(qid)

        model_ready = not missing_answers and (not needs_real or not missing_shot)
        all_ready = all_ready and model_ready
        flag = "READY " if model_ready else "TODO  "
        shot_note = f"real screenshots {len(present_shot)}/{total}" if needs_real else "screenshots: engine proof (ok)"
        print(f"[{flag}] {model:<11} answers {len(answered_ids)}/{total}  |  {shot_note}")
        if missing_answers:
            print(f"           missing answers  (fill responses CSV): q{', q'.join(missing_answers)}")
        if needs_real and missing_shot:
            names = ", ".join(f"q{q}_{model.lower()}.png" for q in missing_shot[:6])
            more = "" if len(missing_shot) <= 6 else f" (+{len(missing_shot) - 6} more)"
            print(f"           missing real screenshots -> save to {shots}/")
            print(f"           e.g. {names}{more}")
    print("-" * 72)
    if all_ready:
        print("ALL REQUIRED CAPTURES PRESENT -> re-run the engine, then verify --strict-screenshots.")
        return 0
    print("NOT READY yet -> fill the missing answers/screenshots above, then re-check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
