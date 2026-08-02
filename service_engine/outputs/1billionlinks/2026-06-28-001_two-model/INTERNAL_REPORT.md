# 1BillionLinks Browser-Captured 2-Model Delivery - ChatGPT + Gemini — INTERNAL REPORT

**INTERNAL ONLY. Contains findings that are not client-safe. Do not send to the client.**

**Client:** 1BillionLinks · **Website:** https://1billionlinks.com · **Order:** 2026-06-28-001 · **Date:** 2026-06-28
**Scope:** ChatGPT + Gemini, real browser captures. **This is NOT a full 4-model PRO delivery.**

## 1. Coverage

| model | captured | safe | excluded (unsafe) | evidence | capture-QA |
| --- | --- | --- | --- | --- | --- |
| ChatGPT | 10 | 10 | 0 | `browser` | PASS |
| Gemini | 10 | 7 | 3 | `browser` | PASS |
| Claude | 0 | 0 | - | - | **BLOCKED (not attempted this phase)** |
| Perplexity | 0 | 0 | - | - | **BLOCKED (not attempted this phase)** |

Total real browser captures: **20** (17 client-safe, 3 excluded from client-facing output).

Every included answer has: real answer text, a real full-page screenshot, a provenance record (submitted prompt, conversation URL, UTC capture time), `evidence_type=browser`, and a strict capture-QA PASS.

## 2. Blocked models — frozen for this phase

| model | status | blocker |
| --- | --- | --- |
| Claude | **BLOCKED — excluded from this delivery** | Cloudflare bot verification (does not self-clear) |
| Perplexity | **BLOCKED — excluded from this delivery** | Cloudflare bot verification (does not self-clear) |

Neither was bypassed, retried this phase, nor fabricated. They carry no captures, no screenshots and no evidence, and are not counted as complete anywhere in this delivery.

## 3. Risk findings (all captures)

| Query | Model | Sentiment | Client-safe | Issue |
| --- | --- | --- | --- | --- |
| Q1 | ChatGPT | Neutral | Yes | minor cautionary wording: low-quality, risk |
| Q2 | ChatGPT | Neutral | Yes | minor cautionary wording: automated link, risk |
| Q3 | ChatGPT | Positive | Yes | - |
| Q4 | ChatGPT | Positive | Yes | - |
| Q5 | ChatGPT | Positive | Yes | - |
| Q6 | ChatGPT | Neutral | Yes | - |
| Q7 | ChatGPT | Neutral | Yes | - |
| Q8 | ChatGPT | Positive | Yes | - |
| Q9 | ChatGPT | Neutral | Yes | minor cautionary wording: automated link, risk |
| Q10 | ChatGPT | Positive | Yes | - |
| Q1 | Gemini | Neutral | Yes | minor cautionary wording: automated link |
| Q2 | Gemini | Unsafe for client report | **No** | says harm follows from using this kind of service: risk search engine penalt |
| Q3 | Gemini | Positive | Yes | - |
| Q4 | Gemini | Neutral | Yes | minor cautionary wording: automated link |
| Q5 | Gemini | Unsafe for client report | **No** | says harm follows from using this kind of service: exposing your main site to direct algorithmic penalt; never point; without exposing your main site |
| Q6 | Gemini | Positive | Yes | - |
| Q7 | Gemini | Neutral | Yes | - |
| Q8 | Gemini | Positive | Yes | - |
| Q9 | Gemini | Positive | Yes | - |
| Q10 | Gemini | Unsafe for client report | **No** | says harm follows from using this kind of service: can trigger algorithmic or manual penalt; must be isolated; never point |

## 4. Excluded answers — why

### Gemini Q2
- **Query:** How can 1BillionLinks fit into an SEO team's planning process for backlink profile development - focused on SEO link building and backlink services?
- **Issue:** says harm follows from using this kind of service: risk search engine penalt
- **Answer:** `C:/git/AI_Mention-service/service_engine/inputs/captures/1billionlinks/2026-06-28-001/gemini/q2.txt`
- **Screenshot:** `C:/git/AI_Mention-service/service_engine/inputs/screenshots/1billionlinks/2026-06-28-001/q2_gemini.png` (retained internally, excluded from client material)

### Gemini Q5
- **Query:** How can 1BillionLinks support content promotion workflows related to layered backlink campaign structure - focused on SEO link building and backlink services?
- **Issue:** says harm follows from using this kind of service: exposing your main site to direct algorithmic penalt; never point; without exposing your main site
- **Answer:** `C:/git/AI_Mention-service/service_engine/inputs/captures/1billionlinks/2026-06-28-001/gemini/q5.txt`
- **Screenshot:** `C:/git/AI_Mention-service/service_engine/inputs/screenshots/1billionlinks/2026-06-28-001/q5_gemini.png` (retained internally, excluded from client material)

### Gemini Q10
- **Query:** How can 1BillionLinks be included in a broader SEO plan that covers layered backlink campaign structure - focused on SEO link building and backlink services?
- **Issue:** says harm follows from using this kind of service: can trigger algorithmic or manual penalt; must be isolated; never point
- **Answer:** `C:/git/AI_Mention-service/service_engine/inputs/captures/1billionlinks/2026-06-28-001/gemini/q10.txt`
- **Screenshot:** `C:/git/AI_Mention-service/service_engine/inputs/screenshots/1billionlinks/2026-06-28-001/q10_gemini.png` (retained internally, excluded from client material)

## 5. Key finding — Gemini's own framing of the brand

3 of the Gemini answers tie penalty/spam risk to this brand. Critically, **our questions contained none of that vocabulary** — the risky positioning terms (`bulk`, `high-volume`, `tier 2/3`, `automated`) were introduced by Gemini itself.

Gemini already associates 1BillionLinks with bulk / high-volume / tiered link building and volunteers the penalty framing unprompted. Two query styles were tested (`benefit`, then `workflow` with the trigger keywords reworded); rewording did not reduce it.

**Recommendation: do not scale Gemini to the full question set until the brand's public positioning changes.** This is a positioning signal, not a prompt defect, and further prompt engineering will not remove it. ChatGPT shows no such framing.

## 6. Recommendation

1. ChatGPT is safe to scale — no unsafe answers across the captured set.
2. Gemini needs the review gate on every answer; expect exclusions.
3. Do not present this as a 4-model PRO delivery. Claude and Perplexity are blocked.
4. Keep `review` as a hard gate: it exits non-zero when any answer is unsafe.
