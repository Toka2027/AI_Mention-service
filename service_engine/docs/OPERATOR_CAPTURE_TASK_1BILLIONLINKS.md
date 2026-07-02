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

### Answers → fill here
`inputs/1billionlinks_responses.csv` — for each row where `model` is ChatGPT / Gemini / Perplexity:
- `answer` — the model's full answer text (verbatim).
- `urls` — links the model gave, `|`-separated.
- `competitors` — competitor brands the model named, `|`-separated.
- `behavior_notes` — anything notable (and the fallback note if full-page wasn't possible).
Leave `screenshot_filename` as-is. **Do not edit the master table by hand** — it is regenerated.

## Then regenerate + verify (from `service_engine/`)
```
python -m engine.main run --input inputs/1billionlinks.json \
  --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 --out outputs

python -m engine.main verify --client-slug 1billionlinks --order-id 2026-06-28-001 \
  --out outputs --strict-screenshots
```
Strict QA must read **OVERALL: PASS**. Then deliver
`outputs/1billionlinks/2026-06-28-001_deliverable.zip`. Also confirm visually that the screenshots are
truly full-page (the gate checks presence + naming, not full-page-ness).

## Definition of done (PRO)
All 4 models captured (100 rows) · all 100 screenshots present · strict QA PASS · ZIP regenerated ·
`report.pdf` fresh · current-state report updated to "full PRO delivery".
