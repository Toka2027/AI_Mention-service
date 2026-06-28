# All-Model Pilot — 1BillionLinks (order 2026-06-28-001)

Goal: one complete pilot with all four PRO models captured — **ChatGPT, Gemini, Claude, Perplexity**.

## Current capture status
| Model | Status | Count |
|---|---|---|
| Claude | ✅ Captured (genuine, 2026-06-28) | 25 / 25 |
| ChatGPT | ⏳ Pending (manual) | 0 / 25 |
| Gemini | ⏳ Pending (manual) | 0 / 25 |
| Perplexity | ⏳ Pending (manual) | 0 / 25 |

- Total captures needed: **100** (25 questions × 4 models). **25 done, 75 pending.**
- The QA gate currently reports **WARN** for "manual screenshots present" until the 75 are added.

## What the operator must do (per pending model)
1. Open the questions: `outputs/1billionlinks/2026-06-28-001/questions.csv` (or `query_plan.md`).
2. Ask each of the 25 questions on the model.
3. **Full-page screenshot** of each answer (rules + fallback: `docs/SCREENSHOT_GUIDE.md`).

### Where screenshots go
Save into:
```
outputs/1billionlinks/2026-06-28-001/screenshots/
```
Exact filenames (lower-case model): `q{ID}_chatgpt.png`, `q{ID}_gemini.png`, `q{ID}_perplexity.png`
(`q1_chatgpt.png` … `q25_chatgpt.png`, etc.). The full list to provide is in
`outputs/1billionlinks/2026-06-28-001/screenshots/EXPECTED_FILES.txt`.

### Where responses go
Edit the capture CSV (the master capture file for this order):
```
inputs/1billionlinks_responses.csv
```
For every pending row (model = ChatGPT / Gemini / Perplexity):
- `answer` — paste the model's full answer text.
- `urls` — any links the model gave, `|`-separated.
- `competitors` — competitor brands the model named, `|`-separated.
- `behavior_notes` — anything notable (and the fallback note if a full-page shot wasn't possible).
Leave the `screenshot_filename` column as-is (already pre-filled with the correct name).

> Tip: a blank, correctly-structured template for this order is also at
> `outputs/1billionlinks/2026-06-28-001/responses_template.csv` if you prefer to start fresh.

## Regenerate the final deliverable after captures are added
```bash
cd service_engine
python -m engine.main run \
  --input inputs/1billionlinks.json \
  --responses inputs/1billionlinks_responses.csv \
  --order-id 2026-06-28-001 \
  --out outputs
```
This rebuilds the master table, pages, report, full-page proof images, links, and the ZIP for the
order (only this order's folder is touched).

## Confirm it's delivery-ready
```bash
python -m engine.main verify --client-slug 1billionlinks --order-id 2026-06-28-001 --strict-screenshots
```
With all 100 captures present, "manual screenshots present" turns PASS and the gate should read
**PASS** (exit 0). Then deliver `outputs/1billionlinks/2026-06-28-001_deliverable.zip`.
