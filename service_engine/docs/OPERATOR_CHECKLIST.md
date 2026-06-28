# Operator Checklist — AI Mention Order Delivery (SOP)

Repeatable steps for delivering one order. Tick each item. One order = one
`outputs/<client-slug>/<order-id>/` folder.

## 0. Intake review
- [ ] Order received with a unique **order id** (e.g. SEOeStore order number).
- [ ] Client provided all **required** fields (see `docs/CLIENT_REQUIREMENTS.md`).
- [ ] Recommended fields collected; **intake completeness ≥ 8/10** (else chase the client).
- [ ] Confirm `topics_to_avoid` and `compliance_notes` with the client.

## 1. Input validation
- [ ] Create `inputs/<client-slug>.json` with `order_id` + intake fields.
- [ ] Questions-only run to validate:
      `python -m engine.main run --input inputs/<client>.json --order-id <ORDER> --out outputs`
- [ ] Resolve any engine warnings (keyword count, package, intake completeness).

## 2. Question generation (STEP 2)
- [ ] Review `outputs/<client>/<order>/questions.csv` — brand + keyword + niche present, on-topic.
- [ ] Confirm no questions touch `topics_to_avoid`.

## 3. Manual LLM query testing (STEP 3)
- [ ] Ask each question on every in-scope model (see package).
- [ ] Capture a **full-page screenshot** per question×model (see `docs/SCREENSHOT_GUIDE.md`).
- [ ] Save shots to the order's `screenshots/` using `q{id}_{model}.png`.

## 4. Response CSV filling (STEP 3→4)
- [ ] Paste each answer into `responses_template.csv` → save as
      `inputs/<client>_<order>_responses.csv`.
- [ ] Fill `urls` and `competitors` (pipe `|` separated); add `behavior_notes`.
- [ ] Cross-check the screenshot filename matches each row.

## 5. Build deliverables (STEP 4–7)
- [ ] Full run:
      `python -m engine.main run --input inputs/<client>.json --responses inputs/<client>_<order>_responses.csv --order-id <ORDER> --out outputs`
- [ ] Confirm the responses-mismatch warning did **not** fire (right file for this order).
- [ ] Review `master_table.csv`, `competitor_frequency.csv`, `source_frequency.csv`.
- [ ] Review `pages/` (brand + keyword + answer + schema + internal links).

## 6. Client-safe review (CRITICAL)
- [ ] Read `report.pdf` and a sample of `pages/*.html` against `docs/CLIENT_SAFE_NOTES.md`.
- [ ] No banned wording; no guarantees of AI mentions / visibility / indexing / rankings / influence.
- [ ] Captured answers don't expose anything off-limits per `topics_to_avoid`.

## 7. QA
- [ ] `screenshots/EXPECTED_FILES.txt` has **zero** unticked `[ ]` items (all manual shots present).
- [ ] All `pages/*.html` open and internal links resolve.
- [ ] `manifest.json` order block shows the correct brand/order/package.
- [ ] `order_brief.md` matches the actual client (guards against data mixing).

## 8. Package & deliver (STEP 7)
- [ ] Confirm `<order-id>_deliverable.zip` was generated for THIS order (unique name).
- [ ] Deliver the ZIP to `delivery_contact`.
- [ ] If publishing pages: complete `submission_checklist.md` (publish + sitemap + crawl request).

## 9. Close
- [ ] Archive the order folder; record the order id as delivered.
