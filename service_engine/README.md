# AI Mention – AI Visibility Baseline & LLM Query Testing (MVP)

A lightweight engine that implements the **AI Mention** micro-service: it **tests how AI tools
currently answer brand-focused questions**, **captures those answers**, **reviews brand/entity
associations and visibility gaps**, and builds **crawlable support pages** from the tested questions
and findings — then packages everything into a report and delivery ZIP.

**It is not a general SEO tool.** It is an *observational baseline*: it documents current AI
behaviour and makes **no attempt to inject, train, manipulate, or influence** AI models, and **no
promise or guarantee** of AI mentions, search rankings, or indexing.

> **Source document:** the *"AI Mention"* service brief.
> **First / pilot client:** [1BillionLinks](https://1billionlinks.com/).

---

## What the service does (the 7 documented steps)

| Step | What | Automated here? |
|------|------|-----------------|
| 1 | Collect inputs (brand, website, 3–7 keywords, niche, package) | ✅ validated from a JSON file |
| 2 | Generate the question set (10 / 25 / 50) | ✅ from the documented templates |
| 3 | Test the AI tools + capture current answers/screenshots | ⚙️ **manual**; engine emits a capture template + query plan |
| 4 | Build the master data table (URLs, competitors, frequency, brand appearances) | ✅ from the filled capture file |
| 5 | Build crawlable support pages (question + AI answer + brand variations + keyword paragraph + URLs + schema + internal links) | ✅ |
| 6 | Publish & make crawlable (sitemap, internal links, crawl request) | ⚙️ engine emits `sitemap.xml` + a manual checklist |
| 7 | Prepare deliverables (PDF report, CSV table, screenshots, support-page URLs, ZIP) | ✅ |

The engine **never calls an LLM itself** — real model answers and screenshots are supplied via the
capture file (this matches the document's manual "internal team workflow" for STEP 3). The service is
**observational**: it documents how AI tools currently respond; it does not influence them.

## Packages

| Package | Questions | Models | Support pages | Schema |
|---------|-----------|--------|---------------|--------|
| BASIC ($29) | 10 | ChatGPT, Gemini | 5 | no |
| PRO ($59) | 25 | ChatGPT, Gemini, Claude, Perplexity | 12 | yes |
| ELITE ($99) | 50 | + Perplexity, Llama (5 total) | 25 | yes (strong) |

---

## Install

```bash
cd service_engine
python -m pip install -r requirements.txt
```

Dependencies are minimal: `fpdf2` (PDF report) and `Pillow` (PNG screenshots). Everything else is
the Python standard library.

## Run

```bash
# Full pilot run (questions + capture template + master table + pages + sitemap +
# PDF + full-page screenshots + links + order brief + ZIP)
python -m engine.main run \
  --input inputs/1billionlinks.json \
  --responses inputs/1billionlinks_responses.csv \
  --order-id 2026-06-28-001 \
  --out outputs

# Questions-only run (STEP 1–3 + previews). Generates the question set and an empty
# capture template to fill manually; pages/tables show "[pending capture]".
python -m engine.main run --input inputs/1billionlinks.json --order-id 2026-06-28-001 --out outputs
```

`--order-id` makes each order self-contained. If omitted, the engine uses `order_id` from the input
JSON, else `order-001` (with a warning). Output goes to **`outputs/<client-slug>/<order-id>/`** and the
ZIP to **`outputs/<client-slug>/<order-id>_deliverable.zip`** — re-running one order never overwrites
another. See [Multi-order & operations](#multi-order--operations).

## Test

```bash
python -m pytest -q
```

---

## Input format

`inputs/<client>.json`:

```json
{
  "brand": "1BillionLinks",
  "brand_variations": ["1 Billion Links", "1BL", "OneBillionLinks"],
  "website": "https://1billionlinks.com",
  "keywords": ["SEO link building", "backlinks", "press release distribution",
               "domain authority", "tier 2 and tier 3 backlink campaigns"],
  "niche": "SEO link building and backlink services",
  "package": "PRO"
}
```

Rules: `brand`, `website` (http/https) and `niche` required; **3–7 keywords**; `package` ∈
{BASIC, PRO, ELITE}; `brand_variations` optional (2–4 recommended for PRO/ELITE).

## Workflow with the manual capture step

1. Run **questions-only** → get `outputs/<client>/<order>/responses_template.csv` and `query_plan.md`.
2. The delivery team performs **STEP 3** manually: ask each in-scope model the question, paste each
   current answer into the `answer` column, list URLs and competitors (pipe `|` separated), and save
   each **full-page** screenshot as `q{id}_{model}.png` (see [docs/SCREENSHOT_GUIDE.md](docs/SCREENSHOT_GUIDE.md)).
3. Run again with `--responses <filled csv>` → full deliverables.

---

## Output (`outputs/<client-slug>/<order-id>/`)

```
order_brief.md                     # intake echo + safety constraints (verify before delivery)
questions.csv / questions.json     # STEP 2 question set
responses_template.csv             # STEP 3 capture template (to fill)
query_plan.md                      # STEP 3 manual instructions (incl. full-page screenshots)
master_table.csv                   # STEP 4 master table
source_frequency.csv               # STEP 4 URL frequency
competitor_frequency.csv           # STEP 4 competitor frequency
pages/*.html                       # STEP 5 crawlable support pages (+ JSON-LD on PRO/ELITE)
sitemap.xml                        # STEP 6
support_page_urls.txt              # links: created support pages
source_links.csv                   # links: extracted source URLs
screenshots/*.png                  # STEP 7 full-page answer-proof images (captured answers)
screenshots/EXPECTED_FILES.txt     # full-page screenshot manifest + rules + fallback
report.pdf                         # STEP 7 client report
submission_checklist.md            # STEP 6 publication & crawl checklist
manifest.json                      # file inventory + order metadata
```
The ZIP is written one level up at `outputs/<client-slug>/<order-id>_deliverable.zip`.

## Multi-order & operations

Each order is fully isolated under `outputs/<client-slug>/<order-id>/` with its own ZIP, so multiple
clients/orders never overwrite or mix. Operational docs:

- [docs/CLIENT_REQUIREMENTS.md](docs/CLIENT_REQUIREMENTS.md) — what to collect from the client.
- [docs/OPERATOR_CHECKLIST.md](docs/OPERATOR_CHECKLIST.md) — step-by-step delivery SOP.
- [docs/SCREENSHOT_GUIDE.md](docs/SCREENSHOT_GUIDE.md) — full-page screenshot rules + fallback.
- [docs/CLIENT_SAFE_NOTES.md](docs/CLIENT_SAFE_NOTES.md) — approved positioning / banned wording.
- [docs/READINESS_ASSESSMENT.md](docs/READINESS_ASSESSMENT.md) — readiness score + gaps + next steps.

---

## 1BillionLinks pilot

- Input: `inputs/1billionlinks.json` (PRO; keywords/niche/variations grounded in the live site).
- Capture: `inputs/1billionlinks_responses.csv` — the **Claude** column holds genuine Claude answers
  captured 2026-06-28 (see `inputs/1billionlinks_responses.NOTES.md`); ChatGPT/Gemini/Perplexity are
  left for the team. Claude's low recognition of the brand is recorded honestly and *is* the
  "AI understanding gap" the review surfaces.
- Order id: `2026-06-28-001`. Output: `outputs/1billionlinks/2026-06-28-001/`;
  ZIP: `outputs/1billionlinks/2026-06-28-001_deliverable.zip`.

## Assumptions

1. The supplied PDF == the Google Doc (titles/content match; the live Doc is sign-in gated).
2. Engine is offline and deterministic; STEP 3 query testing and STEP 6 publication are manual.
3. Competitors are human-entered in the capture file; the engine only counts them. URLs are
   auto-extracted from answers and unioned with any human-entered ones.
4. Brand appearance = literal case-insensitive substring match of the brand + variations.
5. Master table is CSV (the document says "Excel/CSV"); the report is a real PDF; screenshots are PNG
   proof cards for captured answers plus a filename manifest for the manual captures.
6. Support-page URLs are the *intended* URLs (`website/slug.html`); actual hosting + publication is
   performed manually (engine emits the sitemap + checklist). Publication enables crawling; it does
   not guarantee indexing, rankings, or AI mentions.
7. 1BillionLinks keywords/niche/variations were inferred from the website and should be confirmed
   with the client before a paid delivery.

## Out of scope (deliberately not built)

Keyword research, rank tracking, backlink/SEO audits, traffic analytics, CTA/landing pages,
competitor *analysis* beyond counting what the LLM named, dashboards, multi-tenant accounts,
scheduling, or any automated LLM API calls. None of these are in the service document.
