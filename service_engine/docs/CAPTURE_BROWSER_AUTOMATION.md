# Real Capture — Browser Automation (Playwright, human-in-the-loop)

Produces **real** LLM answers + **real** full-page screenshots, labelled `evidence_type=browser`.
Runs on the **operator's machine** in a real Chrome, with the operator's own accounts. It does **not**
bypass login, MFA, CAPTCHA, rate limits, and uses **no stealth or anti-detection patches** — the
operator signs in manually in a persistent browser profile; the engine automates the repetitive
submit → wait → extract → screenshot loop.

> Verified working on Windows 11 + Python 3.12 + Playwright 1.61 driving installed Google Chrome.
> This layer cannot run in CI (no browser, no accounts). Everything else runs everywhere.

## A. Install capture dependencies
```
python -m pip install -r requirements-capture.txt
```

## B. Install the browser
Playwright prefers your **installed Google Chrome** (`channel="chrome"`). Install the bundled
Chromium as a fallback:
```
python -m playwright install chromium
```

## C. Sign in once per model (session persists)
```
python -m engine.main login --model chatgpt
```
Opens Chrome at the model's URL with the persistent profile at `~/.aimention/sessions/<model>/`.
Sign in (MFA/consent as normal), then press Enter in the terminal. The engine stores **no
credentials** — only the browser's own session state, in your own profile directory.

## D. Smoke test — 1 model × 1 question
Always prove the flow before a full run:
```
python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 \
  --models chatgpt --smoke
```
`--smoke` forces exactly one model and one question. Add `--login-wait` to pause for sign-in.

## E. Full capture — 1 model × 25 questions
```
python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 \
  --models chatgpt --questions 1-25 --resume
```
`--resume` skips questions already captured, so an interrupted run continues safely.

## F. All required models (full PRO delivery)
```
python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 \
  --models chatgpt,gemini,perplexity --questions 1-25 --resume --login-wait
```

## Useful flags
| flag | effect |
|---|---|
| `--smoke` | exactly 1 model × 1 question |
| `--login-wait` | pause for manual sign-in before capturing |
| `--confirm-each` | operator presses Enter before each screenshot |
| `--timeout N` | seconds to wait for one answer (default 180) |
| `--resume` | skip already-captured questions |
| `--headless` | hide the window (**not** recommended — see Bot checks) |
| `--prepare-only` | write prompt files only, no browser |

## What one successful capture writes
```
inputs/captures/<slug>/<order>/<model>/q{id}.txt            real answer text
inputs/captures/<slug>/<order>/<model>/q{id}.evidence.txt   literally "browser"
inputs/captures/<slug>/<order>/<model>/q{id}.capture.json   provenance record
inputs/captures/<slug>/<order>/<model>/q{id}.urls.txt       URLs in the answer (if any)
inputs/screenshots/<slug>/<order>/q{id}_{model}.png         real full-page screenshot
inputs/captures/<slug>/<order>/<model>/evidence.jsonl       per-question run log
```
The provenance record is what makes the claim checkable — it stores the exact submitted prompt, the
real conversation URL, the UTC capture time, the browser used, and the screenshot's byte size and
pixel dimensions. Failures are logged and skipped, **never fabricated**.

## G/H/I. Verify, then deliver
```
# strict QA on the browser evidence itself
python -m engine.main capture-qa --input inputs/1billionlinks.json \
  --order-id 2026-06-28-001 --model chatgpt --questions 1

# ingest -> regenerate everything -> strict order QA -> ZIP
python -m engine.main deliver --input inputs/1billionlinks.json \
  --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 --out outputs \
  --require-evidence ChatGPT,Gemini,Perplexity
```
`capture-qa` fails unless the answer is real non-placeholder text, the evidence marker is exactly
`browser`, the submitted prompt matches the generated question, the page URL is on that model's real
host, and the screenshot is a real PNG at real browser dimensions.

## Answer-completion detection
The capturer waits for the answer text to stop changing for 4 consecutive 1.5s polls **and** for the
model's "generating" indicator to disappear. Because a persistent profile can restore the previous
conversation, it also baselines the answer text before submitting, so a restored answer is never
mistaken for the new one. Before screenshotting it grows the viewport to the conversation's full
height — chat UIs scroll internally, so a plain full-page screenshot would otherwise clip the answer.

## Bot checks (important, and not something we work around)
These sites run bot verification. Observed on 2026-07-27 from this machine:

| model | headless | headful (real Chrome) |
|---|---|---|
| ChatGPT | Cloudflare interstitial | **loads normally — capture verified end-to-end** |
| Perplexity | Cloudflare interstitial | loads normally |
| Claude | Cloudflare interstitial | Cloudflare interstitial (operator must clear it in the window) |
| Gemini | loads | loads (sign-in may still be refused, see below) |

Run **headful**. If a verification page appears, the operator completes it in the window — that is
human-in-the-loop, which is allowed. Do not add stealth flags or automation-detection patches.

Google may refuse sign-in in an automation-controlled browser. If that happens, do **not** try to
work around it: capture with another model and report Gemini as blocked for this run.

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
screenshot as `inputs/screenshots/<slug>/<order>/q{id}_{model}.png`, and drop the answer text into
`inputs/captures/<slug>/<order>/<model>/q{id}.txt`. Leave no `q{id}.evidence.txt` (it then defaults
to `operator`). Then `deliver`.

## When a selector breaks
`engine/capture/selectors.py` holds every UI-coupled string per model: `url`, `ready`, `input`,
`submit`, `answer`, `streaming`. The runner names the failing key in its error, e.g.
*"selector 'answer' (...) needs updating"* — so fix that key in that file. Nothing else changes.

Known real-world variation already handled: signed-out ChatGPT renders a plain `<textarea>` and
`data-message-role`/`data-assistant-markdown` markup, while the signed-in UI uses the
`#prompt-textarea` contenteditable and `data-message-author-role`. Both are matched.

## Boundaries (must hold)
No login/MFA/CAPTCHA/rate-limit bypass; no stealth; respect each provider's ToS. Never present
`proof`/`api`/`model-authored-insession` as browser proof. Never mark an order complete unless strict
QA (with `--require-evidence`) passes.

## Query modes and the pre-report risk gate

Question generation has two modes (`engine/generator.py`):

| mode | questions | measures | risk |
|---|---|---|---|
| `benefit` (default) | "what services does X provide", "how does X fit an SEO workflow" | whether models describe the service accurately | low |
| `audit` | "what do you think about X", "top alternatives to X" | how models judge the brand | high — verdicts |

Set per client with `"query_mode"` in the input JSON, or `--query-mode` on `questions`.

```
# inspect the set + lint it for risky phrasing (exit 1 if any found)
python -m engine.main questions --input inputs/1billionlinks.json --limit 10

# screen captured answers BEFORE any client report (exit 1 if any are unsafe)
python -m engine.main review --input inputs/1billionlinks.json \
  --order-id 2026-07-27-promptsafety --models chatgpt,gemini --questions 1-10 \
  --out outputs/1billionlinks/2026-07-27-promptsafety
```

`review` classifies each real answer Positive / Neutral / Negative / Unsafe and writes
`sentiment_review.csv` + `.md`. It distinguishes an accusation about the brand ("pointing links at
your money site can trigger penalties … services like X") from ordinary SEO advice ("avoiding spammy
link sources"), so it does not flag every use of the word "spammy". It never edits or hides an
answer — it only labels what was really captured.

---

## Chrome session modes — launch vs attach (CDP)

Two ways to get a browser. **Attach is strongly recommended** for anything Cloudflare
guards (Claude, Perplexity) and for signed-in capture.

| | launch mode (default) | **attach mode (`--connect-cdp`)** |
|---|---|---|
| who starts Chrome | the engine (Playwright) | **the operator** |
| `navigator.webdriver` | `true` | **`false`** |
| automation flags | present (`--enable-automation`) | **none** |
| Cloudflare on claude.ai | **blocked** | **passes** |
| Cloudflare on perplexity.ai | **blocked** | **passes** |
| setup | none | start Chrome once per profile |

### Why attach works and launch does not

Playwright *launching* Chrome adds automation flags and sets `navigator.webdriver=true`.
That is exactly what Cloudflare fingerprints, so a launched browser is challenged even
with a warm profile. Chrome that the **operator** started is an ordinary browser:
verified 2026-07-30 with `navigator.webdriver === false` and **no interstitial on any of
the four sites**. Nothing is bypassed — `--remote-debugging-port` is a standard Chrome
developer feature and every login/CAPTCHA/MFA step is still done by a human.

### A) / B) Start Chrome for attach mode

```
python -m engine.main chrome-start --model claude          # prints the exact command
python -m engine.main chrome-start --model claude --run    # and starts it
```
which is:
```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 ^
  --user-data-dir="%USERPROFILE%\.aimention\chrome-profiles\claude"
```
A dedicated `--user-data-dir` is **required** — Chrome refuses remote debugging on your
default profile. Sign in once in this profile and it persists.

### C) Sign in / verify manually, then confirm the engine can see it
In that Chrome window: sign in, and clear any Cloudflare/MFA prompt yourself. Then:
```
python -m engine.main login --model claude --connect-cdp http://127.0.0.1:9222
```
Prints `READY for capture` or explains exactly what is not ready. It **detaches without
closing your Chrome** — that window holds the session everything else depends on.

### D–F) Capture
```
# D) one question
python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 \
  --models claude --questions 1 --connect-cdp http://127.0.0.1:9222

# E) ten          F) twenty-five        H) resume after a failure
  ... --questions 1-10 ...        ... --questions 1-25 ...        ... --resume
```

### G) / I) Verify and package
```
python -m engine.main capture-qa --input inputs/1billionlinks.json \
  --order-id 2026-06-28-001 --model claude --questions 1-25
python -m engine.main deliver --input inputs/1billionlinks.json \
  --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 --out outputs \
  --require-evidence ChatGPT,Gemini,Claude,Perplexity
```

### Operator vs engine

| operator (human, manual) | engine (automatic) |
|---|---|
| start Chrome with the debug port | attach to it |
| sign in; complete MFA | verify the chat UI is usable |
| clear any Cloudflare/CAPTCHA prompt | submit each question |
| leave the window open | wait for the real answer, extract text |
| — | full-page screenshot + provenance |
| — | `evidence_type=browser`, capture-QA |

The engine starts a **fresh conversation before every question**, so an unrelated thread
left in your tab never lands in the evidence screenshot.
