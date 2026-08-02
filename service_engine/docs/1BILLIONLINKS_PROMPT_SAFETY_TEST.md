# 1BillionLinks — Cross-LLM Prompt Safety Test (10 queries)

**Order:** `2026-07-27-promptsafety` (separate from the pilot order — nothing was overwritten)
**Date:** 2026-07-27 · **Query mode:** `benefit` · **Machine:** operator Windows 11, real Chrome
**Status:** test complete for 2 of 4 models. **1BillionLinks is NOT final.**

> **SUPERSEDED / CORRECTED.** The Gemini figures below were produced by an earlier risk screen
> that had a false-negative class (it excused 'can trigger penalties' style prose). Corrected
> counts: ChatGPT 0 unsafe, **Gemini 2 unsafe**. See
> [1BILLIONLINKS_PROMPT_SAFETY_TEST_V2.md](1BILLIONLINKS_PROMPT_SAFETY_TEST_V2.md) section 2.

## 1. Verdict

The new positive-intent query style is a **large improvement, but it does not eliminate the risk.**

| model | captured | Positive | Neutral | Negative | Unsafe | flagged |
|---|---|---|---|---|---|---|
| ChatGPT | 10/10 | 4 | 6 | 0 | **0** | — |
| Gemini | 10/10 | 3 | 5 | 1 | **1** | Q5, Q8 |
| Claude | 0/10 | — | — | — | — | blocked |
| Perplexity | 0/10 | — | — | — | — | blocked |

Under the old `audit` style, the single question asked produced *"I would avoid 1BillionLinks…
value for serious SEO: 2/10"*. Under the new `benefit` style, ChatGPT produced **zero** unsafe
answers across 10 questions. Gemini still produced 2.

## 2. The 10 test queries (benefit mode)

All 10 pass the risk lint — no judgment, trust, safety, or competitor phrasing.

| ID | Category | Query |
|---|---|---|
| Q1 | Service Explanation | What services does 1BillionLinks provide for SEO link building…? |
| Q2 | Service Explanation | What should users know about the backlinks services offered by 1BillionLinks…? |
| Q3 | Features | What are the main features of 1BillionLinks for press release distribution…? |
| Q4 | Features | How does 1BillionLinks support planning for domain authority…? |
| Q5 | Benefits | How can 1BillionLinks help with tier 2 and tier 3 backlink campaigns…? |
| Q6 | Benefits | How can 1BillionLinks support content promotion and link visibility through SEO link building…? |
| Q7 | Use Cases | What are the possible use cases of 1BillionLinks for agencies or SEO teams working on backlinks…? |
| Q8 | Use Cases | How can 1BillionLinks be used as part of a press release distribution strategy…? |
| Q9 | Audience Fit | What types of SEO users may benefit from 1BillionLinks for domain authority…? |
| Q10 | Workflow Fit | How does 1BillionLinks fit into a broader SEO growth workflow that includes tier 2 and tier 3 backlink campaigns…? |

Full text: `python -m engine.main questions --input inputs/1billionlinks.json --limit 10`

## 3. Sentiment / risk review

Full table: [`sentiment_review.md`](../outputs/1billionlinks/2026-07-27-promptsafety/sentiment_review.md)
· CSV: `sentiment_review.csv`

### The two Gemini answers that are NOT safe to publish

**Gemini Q8** — ties penalty risk directly to using the brand:
> "Directly pointing thousands of low-cost or syndicated links at a client's money site can trigger
> algorithmic or manual spam penalties. **To safely utilize high-volume services like
> 1BillionLinks:** … Never Point Directly to Client Money Sites at Scale."

**Gemini Q5** — frames the brand as a service to be isolated from the client's site:
> "Never point low-quality mass-tier services directly to your main domain (Tier 0). Keep them
> strictly isolated to Tiers 2 and 3 to act as a buffer. … Mass-generated links can sometimes
> consist of low-quality or spammy footprints."

Both are real captures with real screenshots. They are internal findings, not client copy.

## 4. Why the residual risk is not a prompt-wording problem

The flagged answers are not caused by judgment words in the question — the questions contain none.
They appear when a query touches **how the service is used at scale** (`tier 2 and tier 3 backlink
campaigns`, `press release distribution`). Models answer those by attaching standard safety caveats
to bulk link building, because that is how the brand is publicly positioned.

That is a **positioning signal, not a prompt defect.** No amount of question rewording removes it,
and trying to engineer it away would make the deliverable a fiction rather than a measurement.

## 5. Recommendation on scaling to 25

**Scale to 25 on ChatGPT. Do not scale on Gemini without a review gate.**

1. Keep `benefit` mode as the default. It demonstrably works: 0/10 unsafe on ChatGPT vs a damaging
   verdict on the first `audit`-mode question.
2. **Make `review` a required gate before any client report.** It already exits non-zero when any
   answer is unsafe, so it can block delivery automatically.
3. Expect roughly **1–2 flagged answers per 10 on Gemini**. Budget operator review time; do not
   assume a clean run.
4. Consider dropping or rephrasing the *tier 2 / tier 3* keyword for this client — it is the single
   biggest driver of caveat language. That is a client-positioning decision, not an engine change.
5. Complete Claude and Perplexity before treating the cross-model picture as known. Two of four
   models is not a cross-LLM result.

## 6. Evidence produced

```
inputs/captures/1billionlinks/2026-07-27-promptsafety/chatgpt/   q1-q10 .txt .evidence.txt .capture.json
inputs/captures/1billionlinks/2026-07-27-promptsafety/gemini/    q1-q10 .txt .evidence.txt .capture.json
inputs/screenshots/1billionlinks/2026-07-27-promptsafety/        q1-q10_chatgpt.png, q1-q10_gemini.png
outputs/1billionlinks/2026-07-27-promptsafety/sentiment_review.{csv,md}
```
- 20 answer files, 20 provenance records, **20 real screenshots** (130 KB – 565 KB, 1440 px wide).
- Every evidence marker is `browser`. Strict `capture-qa` = **PASS** for both models (10/10 each).

## 7. Models blocked

| model | blocker | note |
|---|---|---|
| **Claude** | Cloudflare "Performing security verification" | needs the operator to clear it in the window |
| **Perplexity** | Cloudflare "Verifying you are human" (intermittent) | one capture got through, but the answer selector returned a citation fragment, not the answer — `selectors.py` `answer` key needs fixing for Perplexity before it is usable |

Neither was bypassed. Both need a human present; Perplexity additionally needs a selector fix.

Note: ChatGPT and Gemini were captured **signed out** (no operator account available to this run).
Gemini answered on Flash-Lite. Signed-in captures may differ — worth re-running the 10 signed in
before scaling.

## 8. Old evidence preserved

The `audit`-mode negative capture is untouched in the pilot order, labelled
`inputs/captures/1billionlinks/2026-06-28-001/chatgpt/_OLD_RISKY_QUERY_STYLE.md`
("Old risky query style — negative answer produced"). Internal only.
`inputs/1billionlinks_audit_baseline.json` pins that order to `audit` mode so it stays reproducible.

## 9. Framing constraint

A `benefit`-mode run measures **whether models can describe the service accurately**. It is not a
reputation baseline — real buyers do ask "is X legit", and the `audit` mode exists to measure that.
A client report built from `benefit` mode must say which mode produced it, and must not be presented
as a complete picture of how AI talks about the brand.
