# Operator Runbook — Signed-in Browser Capture (official method)

The official capture method is **attach to a Chrome the operator started** (CDP).
Nothing is bypassed: the human does every login, MFA and CAPTCHA step; the engine only
submits questions and records what comes back.

**Order:** 1BillionLinks `2026-06-28-001` · **25 questions × 4 models** · query mode `workflow`

---

## A) Start Chrome — ONE window for all four models

```bat
python -m engine.main chrome-start --model all
```
It prints (and `--run` executes) exactly this:

```bat
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\.aimention\chrome-profiles\shared"
```

- One shared profile → **one Chrome, one login session, all four models.**
- The dedicated `--user-data-dir` is **mandatory**: Chrome refuses `--remote-debugging-port`
  on your normal profile.
- **Leave this window open for the whole session.** Closing it ends the verified session.
- Sign-ins persist in that profile, so later runs need no repeat login.

## G) What you do manually — login only

In that Chrome window, open each site and sign in:

| model | URL | what to expect |
|---|---|---|
| ChatGPT | https://chatgpt.com/ | sign in (email/SSO + MFA) |
| Gemini | https://gemini.google.com/app | Google sign-in |
| Claude | https://claude.ai/new | sign in |
| Perplexity | https://www.perplexity.ai/ | sign in (works signed-out too, but sign in for consistency) |

Also, once per site: dismiss cookie/consent dialogs, and if a Cloudflare
"verifying you are human" page appears, complete it yourself. That is the whole of your
manual work. **Do not close the window afterwards.**

## B) Confirm every model is ready (5 seconds, do this before the long run)

```bat
python -m engine.main session-status --connect-cdp http://127.0.0.1:9222
```
```
  chatgpt     READY   signed in, chat input present (ChatGPT)
  gemini      READY   signed in, chat input present (Gemini)
  claude      READY   signed in, chat input present (Claude)
  perplexity  READY   signed in, chat input present (Perplexity)
```
Exit code 0 = all ready. Anything else names the model to sign in. Per-model check:
```bat
python -m engine.main login --model claude --connect-cdp http://127.0.0.1:9222
```
Both **detach without closing your Chrome**.

## C) Capture — 25 questions per model, in this order

Run these one at a time and check the summary line before moving on.

```bat
python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 --models chatgpt    --questions 1-25 --connect-cdp http://127.0.0.1:9222 --resume
python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 --models gemini     --questions 1-25 --connect-cdp http://127.0.0.1:9222 --resume
python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 --models claude     --questions 1-25 --connect-cdp http://127.0.0.1:9222 --resume
python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 --models perplexity --questions 1-25 --connect-cdp http://127.0.0.1:9222 --resume
```

- `--resume` skips questions already captured, so a failed or interrupted run is safe to
  re-run — it continues instead of starting over.
- Expect roughly 30–60s per question, so ~15–25 min per model.
- The engine starts a **fresh conversation before every question**, so an unrelated
  thread never lands in the evidence screenshot.
- Prove one first if you prefer: swap `--questions 1-25` for `--questions 1`.

## D) QA — per model

```bat
python -m engine.main capture-qa --input inputs/1billionlinks.json --order-id 2026-06-28-001 --model chatgpt    --questions 1-25
python -m engine.main capture-qa --input inputs/1billionlinks.json --order-id 2026-06-28-001 --model gemini     --questions 1-25
python -m engine.main capture-qa --input inputs/1billionlinks.json --order-id 2026-06-28-001 --model claude     --questions 1-25
python -m engine.main capture-qa --input inputs/1billionlinks.json --order-id 2026-06-28-001 --model perplexity --questions 1-25
```
Each cell must pass all 11 checks: real answer text, `evidence_type=browser`, provenance
present, submitted prompt matches the generated question, page URL on that model's real
host, and a real PNG at real browser dimensions. Exit 1 on any FAIL.

Then screen every answer for client safety (exit 1 if any answer is unsafe):
```bat
python -m engine.main review --input inputs/1billionlinks.json --order-id 2026-06-28-001 --models chatgpt,gemini,claude,perplexity --questions 1-25 --out outputs\1billionlinks\2026-06-28-001
```

## E) Report + ZIP

```bat
python -m engine.main deliver --input inputs/1billionlinks.json --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 --out outputs --require-evidence ChatGPT,Gemini,Claude,Perplexity
```
Ingests the captures, regenerates the whole package, runs strict QA, writes the ZIP.
**Prints `STATUS: COMPLETE` only when every required model is real `browser` evidence
with a real screenshot.** Anything else means not deliverable.

## F) Where the files land

```
inputs/captures/1billionlinks/2026-06-28-001/<model>/q{1..25}.txt              answer text
inputs/captures/1billionlinks/2026-06-28-001/<model>/q{1..25}.evidence.txt     "browser"
inputs/captures/1billionlinks/2026-06-28-001/<model>/q{1..25}.capture.json     provenance
inputs/captures/1billionlinks/2026-06-28-001/<model>/evidence.jsonl            run log
inputs/screenshots/1billionlinks/2026-06-28-001/q{1..25}_<model>.png           screenshots
outputs/1billionlinks/2026-06-28-001/                                          report package
outputs/1billionlinks/2026-06-28-001_deliverable.zip                           ZIP
```
`<model>` is lower-case: `chatgpt`, `gemini`, `claude`, `perplexity`.
Expected at full completion: **100 answers + 100 screenshots + 100 provenance records.**

## Division of labour

| operator (human) | engine (automatic) |
|---|---|
| start Chrome with the debug port | attach to it |
| sign in to each model; MFA | verify each model is capture-ready |
| clear any Cloudflare/CAPTCHA | submit each question |
| leave the window open | wait for the real answer, extract text |
| — | fresh conversation per question |
| — | full-page screenshot + provenance |
| — | `evidence_type=browser`, capture-QA, risk review |

## If something breaks

| symptom | fix |
|---|---|
| `No Chrome listening on ...` | Chrome not started, or wrong port — redo step A |
| `SIGN IN NEEDED` | sign in to that model in the Chrome window |
| `bot-verification page showing` | complete it yourself in the window, then re-run |
| `selector 'answer' ... needs updating` | the model changed its DOM — edit that key in `engine/capture/selectors.py` |
| run died part-way | re-run the same command; `--resume` continues |
| rate limited | wait, then re-run with `--resume` |

## Not final until

All available models captured as real `browser` evidence, `capture-qa` PASS per model,
`review` clean for anything client-facing, and `deliver` printing `STATUS: COMPLETE`.
