# Readiness Assessment — AI Mention MVP

_As of 2026-06-28, after the operations-layer update (multi-order, full-page screenshots,
extended intake, operator SOP, client-safe notes)._

## Overall: Ready for multiple orders — **74%**

Technically the system can **safely** accept multiple orders now (strong per-order isolation,
intake scoring, safe wording). The remaining gap is **operational**: a decided publishing/hosting
workflow, an automated QA gate, and report polish. Verdict: **accept a handful of real/pilot orders
now with the manual SOP; do not open for hands-off scale until the must-haves below are closed.**

## Breakdown by area
| # | Area | Status | Score | What's missing |
|---|------|--------|-------|----------------|
| 1 | Engine / automation | **Ready** | 88% | Optional xlsx; question localization; model-override not wired. |
| 2 | Manual workflow | **Partially ready** | 75% | SOP written; needs team run-through + per-order time estimates. |
| 3 | Report quality | **Partially ready** | 70% | Text-only PDF; no embedded screenshot thumbnails, no per-question results table, no branded cover. |
| 4 | Client-facing safety | **Ready** | 90% | Disclaimers + banned-words scrub done; still needs human review each order. |
| 5 | Multi-order folder structure | **Ready** | 90% | Per-client/per-order dirs, unique ZIPs, order brief, mismatch guard. |
| 6 | Input validation | **Ready** | 80% | No email-format / duplicate-keyword / language-code checks; website not reachability-tested. |
| 7 | Screenshot workflow | **Partially ready** | 72% | Full-page rules + manifest + fallback done; engine can't confirm shots exist until QA. |
| 8 | Publishing / indexing workflow | **Not ready** | 45% | sitemap + checklist only; **no decided host** for the support pages. |
| 9 | QA process | **Partially ready** | 58% | Manual checklist only; no automated `verify` gate (files present, links resolve, banned-words lint). |
| 10 | Scalability for team ops | **Partially ready** | 62% | Manual STEP 3 is the throughput bottleneck; no order registry/log or batch runner. |

## Multi-order readiness
- **Per-order input file:** ✅ one JSON per client; `order_id` in JSON or `--order-id`.
- **Outputs separated:** ✅ `outputs/<client-slug>/<order-id>/`.
- **Screenshots separated:** ✅ inside each order's `screenshots/`.
- **ZIP without overwriting:** ✅ `outputs/<client-slug>/<order-id>_deliverable.zip` (unique per order;
  re-running an order only clears that order's folder).
- **Naming convention:** ✅ client-slug + order-id (slugified).
- **BASIC/PRO/ELITE without confusion:** ✅ package drives questions/models/pages/schema; printed in
  the run summary, `order_brief.md`, and `manifest.json`.
- **Similar niches/keywords across clients:** ✅ no collision — outputs isolated by client/order and
  page slugs are brand-prefixed.
- **Risk of mixing client data:** ⚠️ low — mitigated by per-order folders, `order_brief.md` echo, and
  a responses↔questions mismatch warning. Residual risk is human (wrong file/order id) → covered by
  the operator QA step.

### Recommended structure (implemented)
```
outputs/
  <client-slug>/
    <order-id>/
      order_brief.md          manifest.json
      questions.csv|json      responses_template.csv   query_plan.md
      master_table.csv        source_frequency.csv     competitor_frequency.csv
      pages/*.html            sitemap.xml
      support_page_urls.txt   source_links.csv
      screenshots/*.png       screenshots/EXPECTED_FILES.txt
      report.pdf              submission_checklist.md
    <order-id>_deliverable.zip
```

## What's missing before selling publicly
### Must-have (blockers)
1. **Decide & document the publishing/hosting workflow** for support pages (a controlled domain or
   subdomain). Without a host, STEP 6 cannot complete for clients.
2. **Automated QA gate** (or a strictly enforced manual sign-off): confirm every expected full-page
   screenshot exists, all page links resolve, and no banned wording is present.
3. **One full end-to-end pilot with all package models captured** (currently only Claude is
   captured) to validate the manual flow and measure delivery time.
4. **Lock public sales/landing copy** to `docs/CLIENT_SAFE_NOTES.md` (no banned wording, no guarantees).
5. **Define commercial terms** (turnaround, scope limits, refund/expectations) — ops, not code.

### Should-have (soon after launch)
- Report polish: embed screenshot thumbnails, a per-question results table, a branded cover.
- `verify`/`qa` CLI subcommand automating area #9.
- Wire `preferred_models` to actually drive the capture matrix.
- Optional `.xlsx` export (the document says "Excel/CSV").
- Question localization by `country`/`language`.
- Order registry/log (a CSV of delivered orders).

### Nice-to-have (later)
- Intake web form that emits the input JSON.
- Operator dashboard / UI.
- ToS-compliant partial automation of STEP 3 via official model APIs (clearly labeled), screenshots
  still manual.
- Batch runner for many orders.

## Recommended next-step sequence
1. **Lock the SEOeStore service-page copy** using `CLIENT_SAFE_NOTES.md` (fast; unblocks messaging).
2. **Build the order intake form** mapping 1:1 to `CLIENT_REQUIREMENTS.md` (clean inputs in).
3. **Decide the support-page hosting** (subdomain/landing host) — closes the biggest gap (#8).
4. **Add the automated QA `verify` step** and finalize the internal SOP run-through (#9, #2).
5. **Produce a sanitized client-facing sample report** from the 1BillionLinks pilot for the sales page.
6. **Run a second pilot** on a different brand/niche to validate multi-order + timing.
7. **Then open for multiple paid orders.**
