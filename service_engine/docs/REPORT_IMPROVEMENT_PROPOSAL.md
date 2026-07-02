# Report Improvement Proposal — AI Visibility Baseline Report

Goal: make the client report feel professional, client-safe, and valuable for website owners and
agencies/resellers — without overpromising. All wording stays in the approved positioning and avoids
any promise of mentions, rankings, indexing, or model influence.

## What's wrong with the current report
- Text-only PDF; no cover branding, no headline metric, no charts/cards, no screenshot thumbnails.
- Findings read flat (bulleted) rather than as a scannable, sellable narrative.
- No short executive summary for decision-makers.

## Proposed structure (improved)
1. **Cover page** — brand name + logo slot, "AI Visibility Baseline Report", package, order id, date,
   prepared-by (SEOeStore), and a one-line scope/disclaimer.
2. **Executive summary (1 page)** — the headline numbers as cards (see below) + 3–5 plain-language
   takeaways and the top recommended next step.
3. **AI Visibility Baseline score** — the observed baseline metric (defined below), shown as a big
   number + a simple gauge/bar, with a clear "this is a point-in-time baseline" note.
4. **Model coverage overview** — which AI tools were tested, # questions, # captures, capture status.
5. **Brand mention findings** — brand appearance rate overall and per model (table + bar).
6. **Competitor association findings** — most-associated competitors (ranked table / horizontal bar),
   framed as benchmarks/opportunity, not threats.
7. **Query-level evidence** — per-question table (question, model, brand appeared Y/N, key sources).
8. **Support pages created** — list of crawlable support page URLs + what each contains.
9. **Screenshots / proof appendix** — full-page screenshot thumbnails (captured) + pending list.
10. **Next steps & recommendations** — prioritized, data-driven, safe.
11. **Delivery summary & disclaimer** — what's included, scope, and the "what this is not" statement.

> Section order rationale: decision-makers read top-down — score + summary first, evidence and
> appendix later. Agencies can hand the first 2–3 pages to a client and keep the appendix for proof.

## Visual hierarchy
- **Cards** (top of exec summary): AI Visibility Baseline %, Models tested, Questions tested,
  Brand appearances, Support pages created, Top competitor.
- **Tables**: model-by-model brand appearance; competitor frequency; query-level evidence; support URLs.
- **Bars/gauge**: visibility baseline gauge; competitor association bar; per-model appearance bar.
- Consistent heading sizes, a single accent color, generous whitespace, page numbers.

## Defining the "AI Visibility Baseline" metric (safe, computable)
- **Brand Appearance Rate = captured answers that mention the brand ÷ total captured answers** (already
  in the data: `brand_appeared = Y`). Show as a %, labeled "observed baseline, point-in-time."
- Optional secondary: **per-model appearance rate** and **share-of-voice vs top competitor** (brand
  mentions ÷ (brand + top-competitor mentions)). Clearly observational; never a guarantee.

## How to show each part
- **Model-by-model findings:** table — Model | Questions | Captured | Brand-appeared | Appearance %.
- **Screenshots/proof:** thumbnail grid in the appendix, each labeled `q{id}_{model}` with a caption;
  pending ones listed as "to be captured."
- **Competitor associations:** ranked table + horizontal bar of `competitor_frequency.csv`.
- **Brand appearance frequency:** count + % card, plus the per-model bar.
- **Support page URLs:** simple list/table (from `support_page_urls.txt`) with the keyword each targets.
- **Next-step recommendations:** 3–5 prioritized bullets generated from the data (gap keywords, models
  to recapture, competitors to benchmark) + the re-test cadence note.

## Executive summary version (yes — add one)
Add a **1–2 page executive summary PDF** (cards + takeaways + next step) for busy stakeholders and as
a reseller leave-behind, with the full report as the detailed companion.

## Suggested cards (exec summary)
`AI Visibility Baseline: NN%` · `Models tested: N` · `Questions tested: N` · `Brand appearances: N` ·
`Support pages: N` · `Most-associated competitor: <name>`.

## Auto now vs needs manual / new code
**Generatable automatically now (data already exists):**
- All numbers: brand appearance rate, per-model rates, competitor/source frequency, counts.
- Query-level evidence table, support page URL list, captured-screenshot inventory.
- A text executive summary.

**Needs new (small) engineering — "should-have", not yet built:**
- Branded cover, cards, charts/gauges, embedded screenshot thumbnails, the polished layout, and the
  separate executive-summary PDF. (Chart rendering can reuse Pillow/fpdf2 — no new heavy deps.)

**Always manual:**
- The model answers/screenshots themselves; final client-safe human review before sending.
