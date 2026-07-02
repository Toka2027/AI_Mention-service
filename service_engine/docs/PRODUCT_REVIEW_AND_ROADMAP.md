# Product Review & Roadmap — AI Mention (AI Visibility Baseline)

Positioning: **AI visibility baseline · LLM query testing · AI mention discovery · brand/entity
association review · crawlable support pages · AI visibility support assets · competitor association
insights.** No guarantees of AI mentions, LLM visibility, indexing, rankings, model training, or
model influence.

---

## Task 1 — Current status review

### Readiness
- **Engineering readiness: ~88%** (merged MVP: engine, multi-order, QA gate, CI, docs).
- **Sellable-service readiness (end-to-end): ~70%** — blocked by operations (live host, one completed
  all-model pilot, published sales page, pricing/turnaround sign-off, report polish).

### What is already working
- Deterministic engine: intake validation → question generation → master table → crawlable support
  pages (+ schema) → sitemap → report PDF → proof PNGs (for captured answers) → links → ZIP.
- Multi-order isolation (`outputs/<client-slug>/<order-id>/`) + unique ZIP; order brief; no mixing.
- Automated **QA gate** (`verify`, with `--strict-screenshots`).
- Client-safe wording enforced; banned-promise scan in QA.
- Docs: intake requirements, intake-form structure, operator checklist + runbook, screenshot guide,
  QA gate, hosting workflow, sample report, readiness/PR checklists.
- CI (GitHub Actions) green; 28 tests passing. Merged to `main` (`fbc4cd4`).

### What is still manual
- STEP 3 model testing + **full-page screenshots** for ChatGPT/Gemini/Perplexity (Claude captured).
- Publishing support pages + sitemap (STEP 6) on a host.
- Final client-safe review of each report before delivery.

### What is risky
- **Fulfillment throughput**: manual multi-model capture is the bottleneck and the main cost/time driver.
- **Quality perception**: support pages must be genuinely useful; avoid near-duplicate pages at scale.
- **Expectation management**: must consistently message "baseline/testing/reporting," never guarantees.
- **Report polish**: current PDF is text-only — fine for pilot, thin for premium/agency sales.
- **Host dependency**: no live host yet → STEP 6 cannot complete for clients.

### What is missing before selling
Live host (Option C), one completed all-model pilot with **strict QA PASS**, published SEOeStore
service page + intake form, finalized pricing/turnaround, and the sample report linked publicly.

### What is missing before scaling
Report polish (charts/thumbnails/branded cover), an order registry/log, refined SOP timings, and
optionally a lightweight intake form automation. The capture step stays manual.

### Can we accept orders?
- **A. Internal pilot orders — YES.** Ready now.
- **B. Limited paid orders — NOT YET (close).** Needs: host live + one full all-model pilot at strict
  QA PASS + pricing/turnaround set + per-order client-safe review.
- **C. Public SEOeStore orders — NO.** Needs B done + sales page + intake form live + report polish +
  1–2 delivered proofs + support/refund policy.

---

## Task 2 — Roadmap (ordered)

### 1) Must do before selling
1. **Hosting** — provision Option C (SEOeStore support subdomain, per-client/order folders); set client
   `website` to the host base before the final run. *(Status: documented; not provisioned.)*
2. **Full all-model pilot (1BillionLinks)** — capture ChatGPT + Gemini + Perplexity; `verify
   --strict-screenshots` = PASS. Proves fulfillment + real timing. *(Status: 25/100 captured.)*
3. **Pricing & turnaround** — confirm per-package price + delivery time (proposal in the sales page).
4. **SEOeStore service page** — publish (copy ready: `docs/sales/SEOESTORE_SALES_PAGE.md`).
5. **Intake form live** — from `docs/SEOESTORE_INTAKE_FORM.md`.
6. **Sample report linked** — sanitized PDF exists (`docs/samples/`); host it; put link on the page.
7. **Enforce the QA gate** as the delivery checkpoint (exists: `docs/QA_GATE.md`).
8. **Fulfillment SOP** — confirm with the operator (exists: `docs/OPERATOR_CHECKLIST.md` + runbook).

### 2) Should do after the first few orders
- **Report polish**: branded cover, AI Visibility Baseline score, model-by-model table, competitor
  cards, screenshot thumbnails, 1-page executive summary. *(Engineering — see report proposal.)*
- **Order registry/log** (CSV of delivered orders) + simple capacity planning from real timings.
- **Refine packages/pricing** from observed effort and demand.
- **Per-keyword/page balance tuning** if clients want specific keyword emphasis.

### 3) Nice to have later
- Intake **web form** that emits the input JSON automatically.
- Operator **dashboard**.
- **ToS-compliant** partial automation of capture via official model APIs (clearly labeled),
  screenshots still manual.
- **Batch runner** for many orders.

> Scope guardrail: none of the above includes SEO audits, keyword research tools, rank tracking,
> automated LLM calls inside the engine, or general dashboards beyond order ops.
