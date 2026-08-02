# 1BillionLinks — Real Browser Capture Status

**Order:** 2026-06-28-001 · **Package:** PRO (25 questions × ChatGPT/Gemini/Claude/Perplexity)
**Date:** 2026-07-27 · **Machine:** operator Windows 11, Python 3.12, Playwright 1.61, Google Chrome

## Status: smoke test PASSED — full capture NOT done

The real browser flow is proven end-to-end. The order is **not** deliverable yet.

## What was actually captured

| item | value |
|---|---|
| model | ChatGPT (chatgpt.com) |
| question | Q1 — "What do you think about 1BillionLinks for SEO link building services (in the SEO link building and backlink services space)?" |
| submitted | yes, typed into the real ChatGPT composer and sent |
| answer | 2,630 chars, read from the real assistant message |
| conversation URL | `https://chatgpt.com/c/6a673ade-aba8-83ea-9350-591e4ef7012b` |
| screenshot | `q1_chatgpt.png`, 1440×2461, 288,414 bytes, full answer visible |
| evidence_type | `browser` |
| capture-qa | **PASS** (11/11 checks) |

Files:
```
inputs/captures/1billionlinks/2026-06-28-001/chatgpt/q1.txt
inputs/captures/1billionlinks/2026-06-28-001/chatgpt/q1.evidence.txt      -> "browser"
inputs/captures/1billionlinks/2026-06-28-001/chatgpt/q1.capture.json      -> provenance
inputs/screenshots/1billionlinks/2026-06-28-001/q1_chatgpt.png            -> real screenshot
outputs/1billionlinks/2026-06-28-001/screenshots/q1_chatgpt.png           -> copied into delivery
```

The answer is a real, unflattering assessment ("I would avoid 1BillionLinks for any website you care
about ranking long-term", value 2/10, citing Trustpilot and Reddit). That is the point of a baseline —
it measures what the model actually says, not what we would like it to say.

## Capture coverage (100 cells = 25 questions × 4 models)

| model | captured | evidence | counts as proof |
|---|---|---|---|
| ChatGPT | 1 / 25 | `browser` | ✅ (that one cell) |
| Gemini | 0 / 25 | none | ❌ |
| Perplexity | 0 / 25 | none | ❌ |
| Claude | 25 / 25 | `model-authored-insession` | ❌ **not browser proof** |

The 25 Claude rows were authored in a build session. They are **not** a real browser capture and are
labelled as such; strict QA rejects them for any model listed in `--require-evidence`.

## Strict order QA: FAIL (correct)

`deliver --require-evidence ChatGPT,Gemini,Perplexity` reports **NOT COMPLETE**:
- `manual screenshots present` — 74 still to capture
- `real browser screenshots (required models)` — 25 missing
- `evidence provenance (required models)` — 74 rows not real browser/operator

All other 24 checks PASS (files, pages, question count, alignment, intake, naming, wording, no
cross-client mixing).

## Platform behaviour observed (headful, real Chrome)

| model | result |
|---|---|
| **ChatGPT** | loads and answers — **recommended**, capture verified |
| Perplexity | loads normally; expect an occasional Cloudflare check the operator clears |
| Claude | Cloudflare verification page; operator must clear it in the window |
| Gemini | page loads; Google may refuse sign-in in an automation-controlled browser |

Headless triggers bot verification on ChatGPT, Perplexity and Claude. **Run headful.** Nothing was
bypassed and no stealth was used, per the project boundaries.

## To finish this order

```
# 1. sign in once (the smoke test ran signed-out; sign in for consistent, higher-quality answers)
python -m engine.main login --model chatgpt

# 2. all 25 questions for ChatGPT
python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 \
  --models chatgpt --questions 1-25 --resume

# 3. verify the evidence
python -m engine.main capture-qa --input inputs/1billionlinks.json \
  --order-id 2026-06-28-001 --model chatgpt --questions 1-25

# 4. repeat for the other required models
python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 \
  --models gemini,perplexity --questions 1-25 --resume --login-wait

# 5. regenerate + strict QA
python -m engine.main deliver --input inputs/1billionlinks.json \
  --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 --out outputs \
  --require-evidence ChatGPT,Gemini,Perplexity
```

Note: logged-out ChatGPT rate-limits after a few questions. Signing in (step 1) is the practical way
to get through 25 — that is normal account use, not a bypass.

## Not final

1BillionLinks 2026-06-28-001 is **not final**. It becomes deliverable only when the required models
are captured as real `browser` evidence with real screenshots **and** strict QA reports
`STATUS: COMPLETE`. Until then the Claude rows must not be presented as browser proof.
