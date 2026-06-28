# Client Requirements (Intake) — AI Mention

What to collect from the client **before** starting an order. The engine only hard-requires the
core fields; the rest are *recommended* and feed the order brief, the report, and the
"intake completeness" score. Capture everything you can — gaps lower delivery quality.

> Positioning reminder: this is an **AI visibility baseline / LLM query testing / brand-entity
> association review** with **crawlable support pages**. We do **not** promise guaranteed AI
> mentions, LLM visibility, indexing, rankings, model training, or model influence.

## Required (engine will not run without these)
| Field (JSON key) | Notes |
|---|---|
| `brand` | Exact brand name. |
| `website` | Full URL incl. `https://`. |
| `niche` | Service category / industry, in plain words. |
| `keywords` | **3–7** target keywords/phrases. |
| `package` | `BASIC`, `PRO`, or `ELITE`. |

## Required for a professional delivery (recommended — warn if missing)
| Field (JSON key) | Why we need it |
|---|---|
| `brand_variations` | 2–4 spellings/abbreviations to detect brand appearances + use on pages. |
| `country` | Market context for the questions/report. |
| `language` | Language the answers should be captured in. |
| `competitors_known` | Seeds competitive-mapping questions and the association review. |
| `target_urls` | Pages the client wants associated with the brand. |
| `preferred_positioning` | How the brand wants to be described (kept factual). |
| `services_to_highlight` | Services/products to emphasise. |
| `topics_to_avoid` | Off-limits claims/topics (compliance & brand safety). |
| `compliance_notes` | Legal/▲sensitive constraints (e.g. "no ranking guarantees"). |
| `delivery_contact` | Email/contact that receives the deliverable. |

## Optional (improves quality)
`brand_descriptions`, `preferred_models` (which AI tools to test — defaults to the package set),
`question_angles`, `example_customers`, `negative_competitors`, `tone_notes`.

## Operational
`order_id` (unique per order — e.g. the SEOeStore order number; can also be passed as `--order-id`),
`client_slug` (defaults to a slug of the brand).

## What happens if inputs are incomplete
1. **Missing a required field** → the engine **stops** with a clear error. Go back to the client.
2. **Missing recommended fields** → the engine **runs** but:
   - prints a warning listing what is missing,
   - records an **intake completeness score** (e.g. `7/10`) in `order_brief.md` and `manifest.json`.
3. **Policy:** do not deliver below an agreed intake threshold (recommended: **≥ 8/10**). Below that,
   request the missing items first; if the client cannot provide them, note the limitation in the
   delivery and proceed only with sign-off.

See `inputs/1billionlinks.json` for a complete, filled example.
