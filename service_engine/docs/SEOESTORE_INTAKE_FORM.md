# SEOeStore Intake Form — AI Mention

Customer-facing order form. Each field maps 1:1 to an input JSON key (see
`docs/CLIENT_REQUIREMENTS.md`). Simple for customers, complete for operations.

> Positioning note for the form header: *"AI Mention tests how AI assistants currently answer
> questions about your brand, reviews your brand/entity associations, and builds crawlable support
> pages — delivered as a baseline report. It does not guarantee AI mentions, rankings, or indexing."*

## Required fields
| Field | JSON key | Required | Helper text | Validation | Example |
|---|---|---|---|---|---|
| Brand name | `brand` | Yes | Your exact brand name as you want it recognised. | Non-empty. | `1BillionLinks` |
| Website URL | `website` | Yes | Your main site (where the brand lives). | Must start with `http://` or `https://`. | `https://1billionlinks.com` |
| Niche / category | `niche` | Yes | What you do, in plain words. | Non-empty, ≤ ~80 chars. | `SEO link building and backlink services` |
| Target keywords | `keywords` | Yes | The phrases you want associated with your brand. | **3–7** items. | `SEO link building; backlinks; domain authority` |
| Package | `package` | Yes | BASIC (10 Q / 2 AIs), PRO (25 Q / 4 AIs), ELITE (50 Q / 5 AIs). | One of BASIC, PRO, ELITE. | `PRO` |

## Recommended fields (for a quality delivery)
| Field | JSON key | Required | Helper text | Validation | Example |
|---|---|---|---|---|---|
| Brand variations | `brand_variations` | Recommended | Other spellings/abbreviations of your name. | 2–4 suggested. | `1 Billion Links; 1BL` |
| Country / market | `country` | Recommended | Primary market for context. | Free text. | `Global (US/EU)` |
| Language | `language` | Recommended | Language answers should be captured in. | Free text. | `English` |
| Known competitors | `competitors_known` | Recommended | Competitors you already know of. | List. | `FATJOE; Loganix` |
| Target URLs | `target_urls` | Recommended | Pages you want associated with the brand. | Valid URLs. | `https://1billionlinks.com/services` |
| Preferred positioning | `preferred_positioning` | Recommended | How you want to be described (kept factual). | Free text. | `Affordable, high-volume backlink campaigns` |
| Services to highlight | `services_to_highlight` | Recommended | Services/products to emphasise. | List. | `link building; press releases` |
| Topics to avoid | `topics_to_avoid` | Recommended | Anything we must NOT say or claim. | List. | `guaranteed #1 rankings` |
| Compliance notes | `compliance_notes` | Recommended | Legal/sensitive constraints. | Free text. | `No ranking guarantees; factual claims only` |
| Delivery contact | `delivery_contact` | Recommended | Email that receives the deliverable. | Valid email. | `owner@brand.com` |

## Optional fields (improve quality)
| Field | JSON key | Required | Helper text | Validation | Example |
|---|---|---|---|---|---|
| Brand description | `brand_descriptions` | Optional | A short blurb about the brand. | Free text. | `We build tiered backlink campaigns…` |
| Preferred AI models | `preferred_models` | Optional | Specific AIs to prioritise (defaults to the package set). | List from ChatGPT/Gemini/Claude/Perplexity/Llama. | `ChatGPT; Claude` |
| Question angles | `question_angles` | Optional | Angles you care about (trust, pricing, comparison…). | List. | `pricing; trust` |
| Example customers | `example_customers` | Optional | Notable customers/use cases. | List. | `agencies; resellers` |
| Negative competitors | `negative_competitors` | Optional | Brands you do NOT want compared to. | List. | `(brand X)` |
| Tone notes | `tone_notes` | Optional | Preferred tone for any written copy. | Free text. | `Professional, no hype` |

## Operational (set by ops, not the customer)
| Field | JSON key | Helper | Example |
|---|---|---|---|
| Order ID | `order_id` | SEOeStore order number (unique per order). | `2026-06-28-001` |
| Client slug | `client_slug` | Folder-safe id; defaults to a slug of the brand. | `1billionlinks` |

## Form behaviour / validation rules
- Block submission if any **required** field is empty or invalid (keywords must be 3–7; website must
  be a URL; package must be one of the three).
- For list fields, accept semicolon- or comma-separated input and split into an array.
- Show a soft "completeness" indicator for recommended fields; **encourage ≥ 8/10** before checkout.
- On submit, generate `inputs/<client-slug>.json` for the engine.

## What happens if inputs are incomplete
- Missing **required** → cannot start; ops requests the field from the customer.
- Missing **recommended** → order can proceed; the engine records an intake completeness score and
  warns. Policy: do not deliver below 8/10 without explicit sign-off (`docs/CLIENT_REQUIREMENTS.md`).
