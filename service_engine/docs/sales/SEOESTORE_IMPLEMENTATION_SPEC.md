# SEOeStore Implementation Spec — AI Visibility Baseline

Practical spec to publish the service page and wire the order flow. Public brand: **SEOeStore**.

## Page
- **Suggested filename:** `ai-visibility-baseline.php` (or marketplace slug `ai-visibility-baseline`).
- **mTtl (meta title):** `AI Visibility Baseline - See How AI Tools Answer for Your Brand | SEOeStore`
- **mDesc (meta description):** `Test how ChatGPT, Gemini, Claude & Perplexity answer about your brand.
  Get captured answers, full-page screenshots, competitor associations, crawlable support pages & a
  report. A point-in-time AI visibility baseline - no guarantees, just clear findings.`

## Hero
- **Image direction:** clean, professional, marketplace-friendly. A brand/entity in the center with
  4 labeled AI-assistant cards (ChatGPT, Gemini, Claude, Perplexity) showing "answer captured" ticks
  and a small report/PDF + screenshot motif. Flat, modern, SEOeStore palette. Avoid sci-fi/"hacking"
  or "manipulating AI" imagery. No real logos if licensing is unclear — use neutral labels.
- **CTA labels:** Primary `Start Your AI Visibility Baseline`; Secondary `View Sample Report`.

## Pricing card structure (3 cards)
Each card: name + internal tier tag, price, 1-line "best for", feature list (questions, keywords,
AI models, support pages, schema, deliverables), delivery time, CTA button.
- Card 1: **Starter** (BASIC) — $29 — "Trying it / small sites"
- Card 2: **Growth** (PRO) — $59 — "Most brands & agencies" — mark as **Most popular**
- Card 3: **Authority** (ELITE) — $99 — "Competitive niches / resellers"
- CTA on each: `Order <Package>`. Map selection to internal `package` = BASIC/PRO/ELITE.

## Order fields
**Required:** brand name; website (http/https); niche; target keywords (3–7); package.
**Recommended (strongly encouraged; show completeness hint):** country; language; brand variations;
competitors known; target URLs; preferred positioning; services to highlight; topics to avoid;
compliance notes; delivery contact (email).
**Optional:** brand description; preferred AI models; question angles; example customers; negative
competitors; tone notes.
**Set by ops:** order id (SEOeStore order number); client slug (auto from brand).
> Maps 1:1 to the engine input JSON (see `docs/SEOESTORE_INTAKE_FORM.md` / `docs/CLIENT_REQUIREMENTS.md`).

### Validation
- Block checkout if required fields missing/invalid (keywords 3–7; website is a URL; package valid).
- List fields accept comma/semicolon input → arrays. Email format check on delivery contact.
- Show an intake "completeness" hint; encourage ≥ 8/10 recommended fields.

## Sample report link placement
- Hero secondary CTA → `SAMPLE_REPORT_LINK_TBD`.
- A dedicated "Sample report" section mid-page (trust builder, not dominant).
- A small "View sample" link inside the pricing area.
- Host the sanitized PDF (`service_engine/docs/samples/1billionlinks_sample_report.pdf`) and replace
  the placeholder.

## Safe disclaimers (must appear)
Footer + "What this is / isn't" block:
> "AI Visibility Baseline is a testing, reporting, and support-asset service. It does not guarantee AI
> mentions, LLM visibility, indexing, or search rankings, and it does not train or influence AI models.
> Findings are a point-in-time baseline."

## Assets needed
- Hero illustration (per direction above).
- 3 pricing cards (responsive).
- Sample report PDF hosted at a public URL.
- A short "How it works" 7-step graphic (optional).
- Favicon/section icons.

## Icons / visuals needed
- AI assistant tiles (neutral labels), screenshot/proof icon, table/CSV icon, page/document icon,
  sitemap icon, checklist icon, ZIP/box icon, shield/"safe expectations" icon.

## Internal notes for admin/team
- On paid order: collect fields → create `inputs/<client-slug>.json` (+ `order_id`).
- Run the engine (questions-only first) → manual STEP 3 capture (full-page screenshots) → fill
  `responses` CSV → re-run → **`verify --strict-screenshots` must PASS** before delivery
  (`docs/QA_GATE.md`, `docs/OPERATOR_CHECKLIST.md`).
- Hosting: use **Option C** (SEOeStore support subdomain, per-client/order folders) per
  `docs/HOSTING_WORKFLOW.md`; set the input `website` to the host base before the final run.
- Delivery times are proposals — confirm real timings from the first full pilot before publishing.
- Keep all customer-facing copy aligned with `docs/CLIENT_SAFE_NOTES.md`.
- Reseller/white-label: deliverables are clean; offer an unbranded option if needed.
