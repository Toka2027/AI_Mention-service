# Operator Capture Task — 1BillionLinks (order 2026-06-28-001, PRO)

Finish the 3 pending models so the order reaches a strict-QA-PASS PRO delivery. **Do not fabricate
answers.** Capture only what the models actually return.

## Status
- Claude: ✅ captured (25/25). ChatGPT / Gemini / Perplexity: ⏳ **pending, 25 each = 75 captures.**

## Do this for EACH pending model — ChatGPT, Gemini, Perplexity
1. Open the questions: `outputs/1billionlinks/2026-06-28-001/questions.csv` (or `query_plan.md`).
   Ask each of the **25** questions on the live model.
2. Take a **full-page screenshot** of each answer (Chrome DevTools "Capture full size screenshot",
   Firefox "Save Full Page", or a full-page extension). It must show the prompt, the complete answer,
   and model/interface context. Fallback: overlapping `_part1/_part2` files + note the reason.
   (Rules: `docs/SCREENSHOT_GUIDE.md`.)

### Screenshot files → save here (persistent input; NOT the output folder)
```
inputs/screenshots/1billionlinks/2026-06-28-001/q{id}_{model}.png
```
Examples: `q1_chatgpt.png`, `q1_gemini.png`, `q1_perplexity.png` … `q25_perplexity.png`.
The engine copies these into the delivered `screenshots/` on the next run and won't overwrite them.
Do **not** put them in `outputs/.../screenshots/` — that folder is regenerated (wiped) each run.

### Answers → drop here (no CSV editing)
Save each answer as a plain-text file in the per-model drop-folder:
```
inputs/captures/1billionlinks/2026-06-28-001/chatgpt/q1.txt … q25.txt
inputs/captures/1billionlinks/2026-06-28-001/gemini/q1.txt … q25.txt
inputs/captures/1billionlinks/2026-06-28-001/perplexity/q1.txt … q25.txt
```
Each `q{id}.txt` = the model's full answer text. Optional per question: `q{id}.urls.txt`,
`q{id}.competitors.txt`, `q{id}.notes.txt` (one item per line; URLs are also auto-extracted).
The engine ingests these into the responses CSV and regenerates everything — you never edit the CSV
or the report. (Advanced alternative: edit `inputs/1billionlinks_responses.csv` directly.)

## Check progress any time (before running the engine)
```
python tools/capture_status.py
```
Shows, per model, answers filled + REAL screenshots present in the input folder, and the exact
filenames still missing. Claude is "proof ok"; ChatGPT/Gemini/Perplexity need real screenshots.

## Then run ONE command (from `service_engine/`)
```
python -m engine.main deliver --input inputs/1billionlinks.json \
  --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 \
  --out outputs --proof-ok-models Claude
```
`deliver` ingests the dropped answers → regenerates master table / pages / report / screenshots / ZIP
→ runs strict QA, and prints **STATUS: COMPLETE** or the exact `[FAIL]` items. (Equivalent manual
sequence if preferred: `ingest` → `run` → `verify --strict-screenshots --proof-ok-models Claude`.)
Strict QA must read **OVERALL: PASS**. `--proof-ok-models Claude` accepts the in-session Claude proof
cards but **requires real browser screenshots for ChatGPT/Gemini/Perplexity** (from the input folder) —
so a PASS genuinely means those captures exist. Then deliver
`outputs/1billionlinks/2026-06-28-001_deliverable.zip`. Also confirm visually that the screenshots are
truly full-page (the gate checks presence + naming, not pixel-level full-page-ness).

## Definition of done (PRO)
All 4 models captured (100 rows) · all 100 screenshots present · strict QA PASS · ZIP regenerated ·
`report.pdf` fresh · current-state report updated to "full PRO delivery".
