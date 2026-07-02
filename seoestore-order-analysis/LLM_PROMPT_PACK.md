# SEOeStore Order-Text — Manual LLM Prompt Pack (Claude vs ChatGPT vs Gemini)

Use this to test how each LLM generates/improves **service order-page text**. Run the **same** prompt
on all three models, then fill the results table. This produces report section **F**.

> Why manual: the current environment cannot reach ChatGPT/Gemini, and Claude/Gmail MCP connectors
> need authorization in an interactive session. Run these in each model's own web UI.

## How to use
1. Paste the **Context preamble** first (once per chat/session).
2. Pick a service and fill the **placeholders** below.
3. Run each prompt (P1–P8) unchanged on Claude, ChatGPT, and Gemini.
4. Capture outputs in the results table; score with the rubric; mark the winner.

## Placeholders (fill once per service)
- `{SERVICE_NAME}` — e.g. "Blog Articles"
- `{SERVICE_CATEGORY}` — e.g. "SEO content"
- `{WHAT_IT_DELIVERS}` — 1 line, e.g. "publish-ready SEO blog articles written around the client's keywords"
- `{AUDIENCE}` — e.g. "website owners, agencies, resellers"
- `{DELIVERY_TIME}` — e.g. "3–5 business days" (leave blank if unknown — do not invent)
- `{PRICE}` — e.g. "$X" (leave blank if unknown)
- `{REQUIRED_FIELDS}` — the real fields from code/DB, e.g. "target URL, keywords, word count, notes"
- `{OPTIONAL_EXTRAS}` — the real extras, e.g. "extra revisions, express delivery"

## Context preamble (paste first, every session)
```
You are writing customer-facing copy for SEOeStore, an SEO services marketplace. Audience: {AUDIENCE}.
Tone: clear, professional, benefit-led, and conversion-focused — cheerful but credible.
HARD RULES:
- Do NOT promise or guarantee rankings, traffic, indexing, backlinks results, or any specific outcome.
- No hype, no fake scarcity, no absolute claims.
- Be concrete and honest; prefer "designed to help / built to" over "will".
- Keep it tight and scannable. Match an SEO marketplace product page.
Return only what each prompt asks for.
```

## Prompts

### P1 — Service title (5 options)
```
Service: {SERVICE_NAME} ({SERVICE_CATEGORY}). It provides {WHAT_IT_DELIVERS}.
Give 5 short marketplace-ready service titles (max ~6 words each), ranked best-first.
```

### P2 — Short description (1–2 sentences)
```
Write a 1–2 sentence short description for the {SERVICE_NAME} service that delivers {WHAT_IT_DELIVERS}.
It must be benefit-led and follow the hard rules (no guarantees). Give 3 variants.
```

### P3 — Order-form helper text (per field)
```
For the {SERVICE_NAME} order form, the fields are: {REQUIRED_FIELDS}.
For EACH field, write one short helper line (max ~12 words) telling the customer exactly what to enter,
with a tiny example in parentheses. Output as: field — helper (example).
```

### P4 — Required-fields recommendation
```
For a {SERVICE_NAME} order that delivers {WHAT_IT_DELIVERS}, recommend the MINIMAL set of required
fields and any optional fields, and one line each on why. Note: the final list must match our system;
this is a recommendation only.
```

### P5 — Extras explanation
```
The {SERVICE_NAME} service offers these extras: {OPTIONAL_EXTRAS}.
Explain each extra in one clear customer-facing line (what it is + the benefit). No guarantees.
```

### P6 — CTA text (soft + strong)
```
Give CTA button labels for the {SERVICE_NAME} order flow:
- 3 softer "learn more / view details" labels
- 3 stronger "order / start" labels
Max 4 words each. Conversion-focused, no hype.
```

### P7 — Validation / help / error messages (per field)
```
For these fields: {REQUIRED_FIELDS}.
For each, write: (a) a friendly required-field error message, (b) a format hint if relevant
(e.g. URL must start with https://). Keep each under ~12 words. Output as a list per field.
```

### P8 — Customer-facing instructions ("what we need + what happens next")
```
Write a short "What we need from you" list and a 3-step "What happens next" for the {SERVICE_NAME}
service delivering {WHAT_IT_DELIVERS}. Required inputs: {REQUIRED_FIELDS}. Extras: {OPTIONAL_EXTRAS}.
Keep it scannable; no guarantees.
```

## Scoring rubric (score each output 1–5)
- **Clarity** — instantly understandable.
- **Accuracy / no-overpromise** — zero guarantees; nothing invented (esp. price/delivery if left blank).
- **Concision** — tight, scannable.
- **Conversion** — compelling without hype.
- **Field-specificity** — helper/validation actually fits the field.
- **Tone fit** — matches SEOeStore marketplace voice.
Total /30. Higher = better.

## Results capture table (fill per prompt × model) → becomes Report Section F
| Prompt | Service | Model (Claude/ChatGPT/Gemini) | Output summary | Score /30 | Best? | Reusable wording | Risky wording to avoid |
|--------|---------|-------------------------------|----------------|-----------|-------|------------------|------------------------|
| P1 |  | Claude |  |  |  |  |  |
| P1 |  | ChatGPT |  |  |  |  |  |
| P1 |  | Gemini |  |  |  |  |  |
| … repeat for P2–P8 … |

## Red-flag wording to reject in ANY model output
"guaranteed rankings", "guaranteed traffic", "guaranteed indexing", "we guarantee", "#1 on Google",
"instant results", "risk-free results", "guaranteed AI mentions/visibility", or any absolute promise.
Replace with "designed to help", "built to support", "aims to", "structured to".
```
