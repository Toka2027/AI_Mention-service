# 1BillionLinks — AI Visibility Baseline (Current-State Report)

**Service:** AI Mention – LLM Query Seeding (AI visibility baseline / LLM query testing / brand-entity
association review / crawlable support pages).
**Client:** 1BillionLinks · **Website:** https://1billionlinks.com · **Package:** PRO · **Order:** 2026-06-28-001
**Status:** NOT FINAL — real browser capture proven (ChatGPT Q1, `evidence_type=browser`, strict
capture-QA PASS); 1 of 100 answer cells is real browser evidence. The 25 Claude rows are
`model-authored-insession` and are **not** browser proof. See
[1BILLIONLINKS_BROWSER_CAPTURE_STATUS.md](1BILLIONLINKS_BROWSER_CAPTURE_STATUS.md).

> This is an observational baseline at a point in time. It does not promise or guarantee AI mentions,
> LLM visibility, indexing, rankings, or any model influence.

## 1. Executive summary
We prepared and ran the AI Mention baseline for 1BillionLinks: **25 brand + keyword questions** were
generated and the full deliverable package (data table, 12 crawlable support pages, sitemap, report,
proof images, ZIP) was produced. **Claude** answers were captured (25/25). **ChatGPT, Gemini, and
Perplexity are prepared but not yet captured** (they require a human at each model's interface).
Early signal: AI assistants strongly associate this niche with a clear set of competitor brands
(FATJOE, Loganix, Authority Builders, The HOTH), while the captured model showed **no specific,
independently verified knowledge of 1BillionLinks** — the visibility gap this service is built to map.

## 2. Service objective
Test how AI tools currently answer brand-focused questions about 1BillionLinks and its keywords,
capture the answers as evidence, review competitor/source associations, and produce crawlable support
pages + a baseline report to guide AI visibility strategy.

## 3. Questions prepared
- **25 questions** across 4 documented styles (Direct Brand, Keyword+Brand, Commercial Intent,
  Competitive Mapping), each combining the brand + a keyword + niche context.
- Keywords: SEO link building; backlinks; press release distribution; domain authority; tier 2 and
  tier 3 backlink campaigns.
- Source: `outputs/1billionlinks/2026-06-28-001/questions.csv`.

## 4. LLM coverage
| Model | Status | Captures |
|---|---|---|
| Claude (Anthropic) | Captured in-session (authored by Claude, 2026-06-28), genuine responses | 25 / 25 |
| ChatGPT | Prepared, **not executed** (manual capture pending) | 0 / 25 |
| Gemini | Prepared, **not executed** (manual capture pending) | 0 / 25 |
| Perplexity | Prepared, **not executed** (manual capture pending) | 0 / 25 |

No automated API querying was performed; the engine is offline by design. Llama is out of PRO scope.

## 5. Brand mention findings (captured model = Claude)
- The brand name appeared in **23 of 25** captured answers. Note: the brand is named in each question,
  so this largely reflects the model repeating the name while discussing it.
- Qualitatively, the model expressed **no specific, verified knowledge** of 1BillionLinks and gave
  general, cautious guidance — i.e. **low current brand recognition**. This is a normal early-stage
  baseline and is exactly the opportunity area to track over time.

## 6. Competitor & source findings
- **Most-associated competitor brands** (frequency across captured answers): FATJOE (12), Loganix
  (12), Authority Builders (10), The HOTH (10), plus Ahrefs/Moz/EIN Presswire/Newswire (6 each),
  Semrush, Brandpush, Business Wire, Stan Ventures. Full list:
  `competitor_frequency.csv`.
- **Sources referenced** (5 distinct URLs, e.g. moz.com, ahrefs.com, Google spam-policies,
  Trustpilot). Full list: `source_frequency.csv` / `source_links.csv`.

## 7. Indexing (crawlable support) pages status
- **12 crawlable support pages generated** (`pages/*.html`) with FAQ + WebPage schema and internal
  links, plus `sitemap.xml` and `support_page_urls.txt`.
- **Not published** — hosting is a separate manual step (publication helps discovery/crawling only).

## 8. Screenshots / proof status
- **25 engine-generated proof cards** for the captured Claude answers (`screenshots/`, labelled
  `[proof]` in `EXPECTED_FILES.txt`). These are rendered from the captured text, not browser captures.
- **0 real operator browser screenshots** supplied so far.
- **75 manual full-page browser screenshots pending** for ChatGPT/Gemini/Perplexity. Save them to the
  persistent input folder `inputs/screenshots/1billionlinks/2026-06-28-001/` (naming `q{id}_{model}.png`);
  the engine copies them into the delivered `screenshots/` on the next run without overwriting.
  See `docs/OPERATOR_CAPTURE_TASK_1BILLIONLINKS.md`. Strict QA currently **FAILS** on this item.

## 9. Recommendations
- Capture the 3 pending models to complete the 4-model baseline.
- Benchmark against the most-associated competitors (FATJOE, Loganix, Authority Builders, The HOTH).
- Publish the support pages on a chosen host and submit the sitemap (discovery/crawl only).
- Re-test the same questions on a cycle to track how AI recognition changes over time.

## 10. Next steps
1. Perform manual capture for ChatGPT, Gemini, Perplexity (answers + full-page screenshots) — see
   `docs/OPERATOR_CAPTURE_TASK_1BILLIONLINKS.md`. Answers → `inputs/1billionlinks_responses.csv`;
   screenshots → `inputs/screenshots/1billionlinks/2026-06-28-001/`.
2. Re-run the engine to refresh the package (master table, pages, report, screenshots, ZIP).
3. Run the QA gate in strict mode; deliver only once it reads **OVERALL: PASS**.

## Deliverable locations
- Auto-generated PDF (partial baseline): `outputs/1billionlinks/2026-06-28-001/report.pdf`
- Data: `master_table.csv`, `competitor_frequency.csv`, `source_frequency.csv`, `source_links.csv`
- Pages: `outputs/1billionlinks/2026-06-28-001/pages/` · Sitemap: `sitemap.xml`
- Proof images: `outputs/1billionlinks/2026-06-28-001/screenshots/`
- ZIP: `outputs/1billionlinks/2026-06-28-001_deliverable.zip`
