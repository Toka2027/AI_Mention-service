# Real Capture — Browser Automation (Playwright, human-in-the-loop)

Produces **real** LLM answers + **real** full-page screenshots, labelled `evidence_type=browser`.
Runs in the **operator's environment** with the operator's own logged-in accounts. It does **not**
bypass login, MFA, CAPTCHA, rate limits, or use stealth — the operator logs in manually in a
persistent browser profile; the engine automates the repetitive submit + capture.

> This layer cannot run in the build/CI environment (no browser, no accounts). Everything else
> (ingestion, extraction, report, QA, packaging) runs everywhere.

## Install (operator machine)
```
pip install -r requirements.txt -r requirements-capture.txt
playwright install chromium
```

## One-time per model: log in
The first capture run for a model opens Chrome at the model's URL and pauses (`--login-wait`).
Log in (handle MFA/consent) in that window, then press Enter in the terminal. The session persists in
`~/.aimention/sessions/<model>/` for future runs. No credentials are stored by the engine.

## Capture command
```
python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 \
  --models chatgpt,gemini,perplexity --headful --login-wait [--resume] [--questions 1-25]
# prepare prompts only (no browser):
python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 --prepare-only
```
For each question it: submits the prompt, waits for the answer (with an operator "press Enter when
done" confirm), extracts the answer text, and saves a **full-page** screenshot. Outputs land in the
correct order paths:
- answer  -> `inputs/captures/<slug>/<order>/<model>/q{id}.txt` (+ `q{id}.evidence.txt` = `browser`)
- screenshot -> `inputs/screenshots/<slug>/<order>/q{id}_{model}.png`
- log -> `inputs/captures/<slug>/<order>/<model>/evidence.jsonl`
Failures are logged and skipped — **never fabricated**. Re-run with `--resume` to fill gaps.

## Then deliver (engine does the rest)
```
python -m engine.main deliver --input inputs/1billionlinks.json \
  --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 --out outputs \
  --proof-ok-models Claude --require-evidence ChatGPT,Gemini,Perplexity
```
`deliver` ingests the captures, regenerates the master table / pages / report / screenshots / ZIP, and
runs strict QA. **STATUS: COMPLETE** only when every required model is a real `browser`/`operator`
capture with a real screenshot.

## Evidence types (provenance, recorded per answer)
| evidence_type | meaning | counts as real for required models? |
|---|---|---|
| `browser` | real browser UI capture + full-page screenshot | ✅ |
| `operator` | human-in-the-loop capture | ✅ |
| `api` | official API (answer text only, no UI proof) | ❌ (label only) |
| `proof` | engine-generated proof card | ❌ |
| `model-authored-insession` | text authored by an assistant in a build session | ❌ |
| `none` | not captured | ❌ |

## If a model blocks automation
Fall back to operator-assisted capture: send the prompt yourself in the browser, save the full-page
screenshot to the screenshots input folder as `q{id}_{model}.png`, and drop the answer text into
`inputs/captures/<slug>/<order>/<model>/q{id}.txt`. Leave no `q{id}.evidence.txt` (defaults to
`operator`). Then `deliver`. The engine still owns validation, reporting, QA, and packaging.

## Selectors
`engine/capture/selectors.py` holds per-model URLs + DOM selectors (best-effort starting points).
These products change their UI often — if capture can't find the input/answer, update selectors there.

## Boundaries (must hold)
No login/MFA/CAPTCHA/rate-limit bypass; no stealth; respect each provider's ToS. Do not present
`proof`/`api`/`model-authored-insession` as browser proof. Do not mark an order complete unless strict
QA (with `--require-evidence`) passes.
