# Second Order — Preparation Only: SEOeStore Panel

**Status: PREPARATION ONLY. Do NOT execute until explicitly approved.** This is the AI Mention /
LLM Query Seeding service run #2 (the first is 1BillionLinks). It is **not** the old SEOeStore PHP
order-page task.

## 1. Required input checklist (collect before execution)
Hard-required (engine blocks without these):
- [ ] Brand name — proposed: **SEOeStore Panel** (confirm exact form).
- [ ] Website — **MISSING / to confirm.** No SEOeStore input exists in `service_engine/`. Candidate
      observed earlier in the session: `https://panel.seoestore.net` — **verify before use; do not
      assume.**
- [ ] Niche / category — to confirm (e.g. "SEO services panel / reseller platform").
- [ ] Keywords — **3–7 required, to confirm** (e.g. SEO panel, backlinks reseller, SEO services API…).
- [ ] Package — to confirm (BASIC / PRO / ELITE).

Recommended intake (raises intake-completeness score; target ≥ 8/10):
- [ ] brand_variations · country · language · competitors_known · target_urls ·
      preferred_positioning · services_to_highlight · topics_to_avoid · compliance_notes ·
      delivery_contact.

## 2. Suggested order folder name
- `client_slug`: **seoestore-panel**
- `order_id`: **YYYY-MM-DD-001** (e.g. `2026-07-02-001`)
- Output would be created at: `outputs/seoestore-panel/<order-id>/`
- ZIP: `outputs/seoestore-panel/<order-id>_deliverable.zip`
- Screenshots input: `inputs/screenshots/seoestore-panel/<order-id>/`

## 3. Suggested JSON input structure (`inputs/seoestore-panel.json`)
```json
{
  "order_id": "2026-07-02-001",
  "client_slug": "seoestore-panel",
  "brand": "SEOeStore Panel",
  "brand_variations": ["SEOeStore", "SEOeStore.net"],
  "website": "<CONFIRM — e.g. https://panel.seoestore.net>",
  "niche": "<CONFIRM>",
  "country": "<CONFIRM>",
  "language": "English",
  "keywords": ["<CONFIRM 3-7 keywords>"],
  "package": "<BASIC|PRO|ELITE>",
  "competitors_known": [],
  "target_urls": [],
  "preferred_positioning": "<CONFIRM>",
  "services_to_highlight": [],
  "topics_to_avoid": ["guaranteed rankings", "guaranteed AI mentions"],
  "compliance_notes": "Factual claims only; no guarantees of rankings/AI mentions/indexing.",
  "delivery_contact": "<CONFIRM email>",
  "tone_notes": "Professional, factual, no hype."
}
```

## 4. What information is needed before execution
1. Confirmed **website URL** for the SEOeStore Panel (currently missing/unverified).
2. Confirmed **niche**, **3–7 keywords**, and **package** tier.
3. Recommended intake fields for a quality delivery (competitors, positioning, topics to avoid, etc.).
4. Operator availability for the **manual multi-model capture** (ChatGPT/Gemini/Perplexity — see lessons).

## 5. Lessons from the 1BillionLinks pilot to apply
- **Only Claude can be captured in-session**; ChatGPT/Gemini/Perplexity require a human at the live
  model UIs. Budget operator time for the 25×3 manual captures.
- **Real screenshots go in the persistent input dir** `inputs/screenshots/<slug>/<order>/`, never the
  output folder (which is wiped each run); the engine copies them in without overwriting.
- **Answers go in the responses CSV**; the master table + pages + report regenerate automatically — do
  not hand-edit outputs.
- **Run strict QA** (`verify --strict-screenshots`) and require **OVERALL: PASS** before delivery.
- **Confirm intake up front** (≥ 8/10) to avoid a partial baseline.
- **Brand-in-question caveat**: `brand_appeared` mostly reflects the model echoing the name; the real
  value is recognition quality + competitor/source associations.
- **Honesty**: label a Claude-only run as a "current-state baseline", not a full PRO delivery.

## 6. Do NOT do yet
Do not create `inputs/seoestore-panel.json`, do not run the engine, do not generate any
`outputs/seoestore-panel/...` — wait for explicit approval and the confirmed inputs above.
