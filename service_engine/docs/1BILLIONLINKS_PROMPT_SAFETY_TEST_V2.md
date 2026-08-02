# 1BillionLinks — Prompt Safety Test v2 (10 queries, `workflow` mode)

**Order:** `2026-07-27-promptsafety-v2` · **Date:** 2026-07-27 · **Query mode:** `workflow`
**Status:** 2 of 4 models captured. **1BillionLinks is NOT final.**

## 1. Headline: v2 did not fix Gemini — and the reason matters

| test | style | ChatGPT unsafe | Gemini unsafe |
|---|---|---|---|
| old | `audit` (judgment) | 1/1 asked | not run |
| v1 | `benefit` (feature-led) | **0/10** | 2/10 (Q5, Q8) |
| **v2** | `workflow` (+ safe keyword aliases) | **0/10** | **3/10** (Q2, Q5, Q10) |

v2 was designed to remove the trigger terms. It did — from *our questions*. It did not help,
because **the model supplies those terms itself.**

### Proof

The v2 questions contain none of the risky positioning vocabulary. Gemini's answers introduce it
anyway:

| query | risky terms in OUR question | risky terms Gemini added in its ANSWER |
|---|---|---|
| Q2 | none | bulk, high-volume, tier 2, tier 3 |
| Q5 | none | bulk, high-volume, tier 2, tier 3, automated |
| Q10 | none | bulk, high-volume, tier 2, automated |

Gemini already associates 1BillionLinks with bulk/high-volume link building and volunteers the
penalty framing unprompted:

> "…flat, uncalculated **bulk link-building can trigger algorithmic or manual penalties**. To safely
> leverage a high-volume service, **it must be isolated to lower, non-risky tiers**." — Gemini, v2 Q10

> "While **bulk link services** can rapidly expand a backlink profile, **improper integration can risk
> search engine penalties**." — Gemini, v2 Q2

> "**Never point** raw, high-volume automated bulk links directly to your primary domain." — Gemini, v2 Q5

**Conclusion: this is not a prompt-wording problem and cannot be solved by rewording.** The framing
comes from what the model already believes about the brand. Rewording our questions only hides the
trigger from us, not from the model.

## 2. Correction to the v1 report

The v1 report stated Gemini had 1 unsafe answer and that v2 scored 0/20. **Both figures were wrong** —
my risk screen had a false-negative class: it excused hazard words whenever an avoidance cue appeared
anywhere in a wide window, so calm advisory prose ("can trigger penalties… to safely leverage…")
passed as safe.

Fixed by adding `CONSEQUENCE_MARKERS` (harm presented as an *outcome* of using the service — never
excusable by a nearby cue) and narrowing the cue window from 90 to 28 characters. Corrected scores
are in the table above; both test folders have been re-scored. Regression tests now cover all four
consequence phrasings plus the mirror case ("the service *helps avoid* penalties" = safe).

## 3. The 10 v2 queries — risk lint: CLEAN

`python -m engine.main questions --input inputs/1billionlinks_v2.json --limit 10` → exit 0.
The lint now also rejects positioning vocabulary (`bulk`, `high-volume`, `tier 2/3`, `low-quality`,
`spam*`, `mass-tier`, `cheap`, `automated links`, `link farms`).

| ID | Category | Query (abbreviated) |
|---|---|---|
| Q1 | Workflow Support | How does 1BillionLinks support SEO workflows that involve SEO link building…? |
| Q2 | Workflow Support | How can 1BillionLinks fit into an SEO team's planning process for backlink profile development…? |
| Q3 | Campaign Organisation | How can 1BillionLinks help organise a press release publishing campaign…? |
| Q4 | Campaign Organisation | What does 1BillionLinks offer for structuring domain authority growth work…? |
| Q5 | Content Promotion | How can 1BillionLinks support content promotion workflows related to layered backlink campaign structure…? |
| Q6 | Link Visibility Planning | How can 1BillionLinks help with link visibility planning for SEO link building…? |
| Q7 | Campaign Tracking | What reporting or tracking options does 1BillionLinks provide for backlink profile development…? |
| Q8 | Agency Use Case | How do agencies typically use 1BillionLinks when managing press release publishing…? |
| Q9 | Distribution Options | What publishing or distribution options does 1BillionLinks offer for domain authority growth…? |
| Q10 | SEO Planning | How can 1BillionLinks be included in a broader SEO plan that covers layered backlink campaign structure…? |

Keyword aliases used (our wording only — answers are never edited):
`tier 2 and tier 3 backlink campaigns` → "layered backlink campaign structure" ·
`press release distribution` → "press release publishing" ·
`backlinks` → "backlink profile development" · `domain authority` → "domain authority growth"

## 4. Capture status per model

| model | queries | answers | screenshots | provenance | evidence | capture-QA |
|---|---|---|---|---|---|---|
| ChatGPT | 10 | 10 | 10 | 10 | `browser` | **PASS** |
| Gemini | 10 | 10 | 10 | 10 | `browser` | **PASS** |
| Claude | 0 | 0 | 0 | 0 | — | **BLOCKED** |
| Perplexity | 0 | 0 | 0 | 0 | — | **BLOCKED** |

**20 of the required 40 screenshots exist.** Claude and Perplexity are not complete and are not
counted as complete.

## 5. Blockers — what was done

**Claude and Perplexity: Cloudflare.** Verified both sit on a "Just a moment…" interstitial that does
**not** self-clear — polled every 5s for 60s (Perplexity) and 50s (Claude); the chat input never
appeared. This is the site's own protection and was not bypassed. Clearing it needs a human at the
browser, which an automated run cannot be.

Improvements made so the operator path works:
- The capturer now **detects the bot-verification page explicitly** and fails with the exact
  remedy instead of a confusing selector error.
- Operator command (human-in-the-loop, allowed):
  ```
  python -m engine.main login --model claude        # clear the check, press Enter
  python -m engine.main capture --input inputs/1billionlinks_v2.json \
    --order-id 2026-07-27-promptsafety-v2 --models claude --questions 1-10 --login-wait --resume
  ```

**Perplexity: fragment bug fixed at the root.** v1 saved a 95-char citation card as an "answer".
Two fixes, both model-agnostic and verified on ChatGPT/Gemini:
1. `_answer_text()` now picks the **largest** matching block, not `.last` — citation cards match the
   answer selector but are always smaller than the answer body.
2. A capture is **rejected** if the extracted text is under 80 chars, with a message naming the
   selector to fix. A fragment can no longer be written to disk or counted as evidence.

The Perplexity `answer` selector still cannot be verified against the live DOM while Cloudflare
blocks the page; `selectors.py` documents exactly what to inspect and re-run.

## 6. Sentiment / risk review

- v2 table: [`outputs/1billionlinks/2026-07-27-promptsafety-v2/sentiment_review.md`](../outputs/1billionlinks/2026-07-27-promptsafety-v2/sentiment_review.md) (+ `.csv`)
- v1 table (re-scored): `outputs/1billionlinks/2026-07-27-promptsafety/sentiment_review.md`

Columns: Query ID · Query · Model · Sentiment · Safe to use? · Issue if unsafe · Answer path ·
Screenshot path. `review` exits non-zero when any answer is unsafe, so it can gate delivery.

## 7. Recommendation: do NOT scale to 25 yet

1. **ChatGPT is safe to scale** — 0 unsafe across 20 captured answers (v1 + v2).
2. **Gemini is not** — 5 unsafe across 20, and v2 made it worse. Scaling to 25 would be expected to
   produce roughly 5–8 unsafe Gemini answers.
3. **Stop iterating on prompt wording for Gemini.** Section 1 shows the trigger is the model's
   existing view of the brand, not our phrasing. A v3 would be more of the same.
4. The real options are business decisions, not engine changes:
   - deliver ChatGPT-only for this client, stating the scope; or
   - deliver Gemini with the unsafe answers excluded **and disclosed** as excluded; or
   - treat the Gemini result as the finding — it is a genuine, evidenced measurement of how a major
     assistant frames this brand, and arguably the most valuable thing in the report.
5. Complete Claude and Perplexity before any cross-LLM claim. Two of four is not a cross-LLM result.

## 8. Evidence preserved — three tests, none overwritten

| test | order folder | style | kept as |
|---|---|---|---|
| old | `2026-06-28-001` | `audit` | "Old risky query style — negative answer produced" (`_OLD_RISKY_QUERY_STYLE.md`) |
| v1 | `2026-07-27-promptsafety` | `benefit` | Prompt Safety Test v1 |
| v2 | `2026-07-27-promptsafety-v2` | `workflow` | Prompt Safety Test v2 (this document) |

Each is a separate order folder with its own captures, screenshots and review table. Inputs are
pinned per test (`1billionlinks_audit_baseline.json`, `1billionlinks.json`, `1billionlinks_v2.json`)
so every result stays reproducible.

## 9. Not final

1BillionLinks 2026-06-28-001 is **not final**. It requires all four models captured as real `browser`
evidence with real screenshots, strict `capture-qa` PASS per model, and a `review` pass with no
unsafe answers in anything client-facing.
