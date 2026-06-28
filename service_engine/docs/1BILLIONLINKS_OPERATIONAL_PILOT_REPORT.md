# 1BillionLinks — Operational Pilot Report

- Service: **AI Mention / LLM visibility baseline** (no SEO audit / ranking / manipulation).
- Client: **1BillionLinks** (first real pilot). Order: **2026-06-28-001**. Package: **PRO**.
- main commit used: `fbc4cd488fa8cb8e63b940bf35678eb45b487e10`.
- Date of this run: 2026-06-28.

## What was run
Ran the merged engine from `main` for the 1BillionLinks order:
`python -m engine.main run --input inputs/1billionlinks.json --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 --out outputs`
→ generated questions, master table, frequency tables, 12 crawlable support pages (+ schema),
sitemap, links, report PDF, 25 answer-proof PNGs, order brief, manifest, and the ZIP.

## Models captured
| Model | Status | Count |
|---|---|---|
| Claude | ✅ Captured (genuine, 2026-06-28) | 25 / 25 |
| ChatGPT | ⏳ Pending (manual) | 0 / 25 |
| Gemini | ⏳ Pending (manual) | 0 / 25 |
| Perplexity | ⏳ Pending (manual) | 0 / 25 |

- **Completed captures: 25 / 100.** **Pending: 75.**
- No model answer was fabricated. ChatGPT/Gemini/Perplexity require a human at the live model UIs;
  that capture has not been performed, so those rows remain `[pending capture]`.

## Screenshots
- Full-page answer-proof PNGs generated for Claude: **25**.
- Manual full-page screenshots still required: **75** (`q{id}_chatgpt.png`, `q{id}_gemini.png`,
  `q{id}_perplexity.png` for q1–q25). List: `outputs/1billionlinks/2026-06-28-001/screenshots/EXPECTED_FILES.txt`.

## QA result
- Non-strict QA: **WARN** (exit 0) — all artifacts present; only "manual screenshots present" warns.
- Strict QA (`--strict-screenshots`): **FAIL** (exit 1) — 75 full-page screenshots still to capture.
- **Per policy, strict QA must PASS before client delivery. It does not. → NOT deliverable yet.**

## Output locations
- Output folder: `service_engine/outputs/1billionlinks/2026-06-28-001/`
- ZIP: `service_engine/outputs/1billionlinks/2026-06-28-001_deliverable.zip`
- Report PDF: `service_engine/outputs/1billionlinks/2026-06-28-001/report.pdf`

## Manual capture packet (operator)
Everything the operator needs is already generated / documented:
- Questions to ask: `outputs/1billionlinks/2026-06-28-001/questions.csv` and `query_plan.md`.
- Models to test: ChatGPT, Gemini, Perplexity (Claude done).
- Screenshot naming: `q{id}_{model}.png` (lower-case model); save to the order's `screenshots/`.
- Where to paste answers: `inputs/1billionlinks_responses.csv` (columns `answer`, `urls`,
  `competitors`, `behavior_notes`; `|`-separated lists).
- Valid full-page screenshot + fallback rules: `docs/SCREENSHOT_GUIDE.md` and
  `screenshots/EXPECTED_FILES.txt`.
- End-to-end steps: `docs/ALL_MODEL_PILOT.md`.

## Support page URL status
- Support pages generated: **12** (`pages/*.html`).
- Generated URLs currently use the input `website` (`https://1billionlinks.com`), e.g.
  `https://1billionlinks.com/1billionlinks-seo-link-building-q1.html`. Full list:
  `support_page_urls.txt`. These are **intended URLs**; the pages are **not published** anywhere yet.

## Hosting status — Option C (operational plan, NOT yet provisioned)
Hosting model: SEOeStore-owned support subdomain with per-client/per-order folders. **The host is not
provisioned; the URL below is a documented PLACEHOLDER, not a live link.**

- Host base URL (placeholder): `https://ai-visibility.<seoestore-domain>/` *(to be provisioned)*
- Expected folder path: `/1billionlinks/2026-06-28-001/`
- Expected final support page URL pattern (placeholder):
  `https://ai-visibility.<seoestore-domain>/1billionlinks/2026-06-28-001/<page-slug>.html`
- Files to upload: everything in the order's `pages/` plus `sitemap.xml`.
- Sitemap location (after publish): `https://ai-visibility.<seoestore-domain>/1billionlinks/2026-06-28-001/sitemap.xml`
- Crawl / indexing checklist: `submission_checklist.md` (publish pages → publish sitemap →
  request crawl → verify internal links → record confirmation). Discovery/crawling only; no
  guarantee of indexing, rankings, or AI mentions.
- Rollback / unpublish: delete the `/1billionlinks/2026-06-28-001/` folder on the host and remove its
  sitemap entry; isolated per order, so no other client/order is affected.
- When the host is decided: set the input `website` to the host base and **re-run the engine** so the
  generated URLs and `sitemap.xml` match the live location, then re-run QA.

## Remaining blockers
1. **Capture the 75 pending full-page screenshots + answers** (ChatGPT, Gemini, Perplexity).
2. **Strict QA must PASS** (`verify --strict-screenshots`).
3. **Option C host provisioned**; set `website` to the host base and re-run; publish pages + sitemap.
4. **Pricing / turnaround / scope sign-off** + brand-safety sign-off.

## Deliverable?
**No — not deliverable.** Strict QA FAILS (75 pending captures) and the host is not provisioned. The
package structure, the 25 genuine Claude captures, and all automated artifacts are complete and
correct; the order becomes deliverable once the manual multi-model capture is finished and strict QA
passes.
