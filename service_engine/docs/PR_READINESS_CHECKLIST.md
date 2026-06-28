# PR / Launch Readiness Checklist — AI Mention

Gate each stage before promoting it. Tick every box; a stage is "ready" only when its list is fully
checked. Stay within the AI Mention / LLM visibility scope and the 1BillionLinks pilot.

## Internal pilot checklist (Stage A)
- [x] Engine runs end-to-end (`run` produces all artifacts).
- [x] Multi-order isolation (`outputs/<client-slug>/<order-id>/` + unique ZIP).
- [x] Extended client intake + completeness score.
- [x] Full-page screenshot SOP + manifest.
- [x] Automated QA gate (`verify`) passing on a complete order.
- [x] Client-safe wording enforced (no banned promises).
- [x] Tests green (28 passed).
- [x] Operator SOP + runbook documented.

## Limited paid order checklist (Stage B)
- [ ] Option C host live; client `website` points to the real host base.
- [ ] One full **all-model** pilot captured (ChatGPT + Gemini + Claude + Perplexity).
- [ ] `verify --strict-screenshots` returns **PASS** on that order.
- [ ] Brand-safety review signed off (`CLIENT_SAFE_NOTES.md`).
- [ ] Pricing, turnaround, and scope/expectations defined (non-code).
- [ ] Intake collected at **≥ 8/10** completeness.
- [ ] Delivery ZIP sent + `submission_checklist.md` completed.

## Public launch checklist (Stage C)
- [ ] SEOeStore service page copy locked to approved positioning (no guarantees).
- [ ] Customer intake form built from `SEOESTORE_INTAKE_FORM.md`.
- [ ] Sanitized sample report published for sales (`docs/samples/`).
- [ ] Report polish shipped (screenshot thumbnails, per-question table, branded cover).
- [ ] 1–2 paid orders delivered as proof (Stage B passed).
- [ ] Hosting + QA + SOP documented for the team and rehearsed.
- [ ] Support/refund + expectation-setting policy published.

## Hosting setup checklist — Option C (SEOeStore subdomain, per-client/order folders)
- [ ] Create a support subdomain on an SEOeStore-owned domain
      (e.g. `ai-visibility.seoestore-domain.com`), clearly labeled as an SEOeStore property.
- [ ] Decide the path convention: `/<client-slug>/<order-id>/<page-slug>.html`
      (mirrors `outputs/<client-slug>/<order-id>/pages/`).
- [ ] Set the client input `website` to the host base so generated URLs + `sitemap.xml` match.
- [ ] Static hosting + HTTPS; ability to publish/unpublish a single client folder.
- [ ] Publish the order's `pages/` + `sitemap.xml`; verify internal links resolve.
- [ ] Submit the sitemap / request a crawl; record in `submission_checklist.md`.
- [ ] Keep pages genuinely useful; do not mass-produce near-duplicate pages across clients.
- Expected URL example: `https://ai-visibility.seoestore-domain.com/1billionlinks/2026-06-28-001/1billionlinks-seo-link-building-q1.html`

## Screenshot capture checklist (per order)
- [ ] One **full-page** screenshot per question × model (not cropped).
- [ ] Each shot shows the prompt, the full answer, and model/interface context.
- [ ] Filenames exactly `q{id}_{model}.png` (lower-case model) in the order's `screenshots/`.
- [ ] Fallback `_part1/_part2.png` used + noted in `behavior_notes` when full-page isn't possible.
- [ ] `EXPECTED_FILES.txt` has zero remaining `[ ]` items.
- See `docs/SCREENSHOT_GUIDE.md`.

## Report polish checklist (Stage C should-have)
- [ ] Embed full-page screenshot thumbnails in the PDF.
- [ ] Per-question results table (model × brand-appeared) in the PDF.
- [ ] Branded cover (logo, client name, order id, date).
- [ ] Optional `.xlsx` export alongside the CSV master table.

## QA gate command checklist (before every delivery)
- [ ] `python -m engine.main verify --client-slug <slug> --order-id <id> --out outputs`
- [ ] For a full delivery add `--strict-screenshots` (missing manual shots become FAIL).
- [ ] Resolve every `[FAIL]`; review every `[WARN]`.
- [ ] Exit code 0 before sending the ZIP.
- See `docs/QA_GATE.md`.
