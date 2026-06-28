# AI Mention – LLM Query Seeding (MVP)

A lightweight engine that implements the **AI Mention** micro-service exactly as described in the
service document: seed brand-focused questions into major LLMs, capture the answers, and turn them
into crawlable **indexing pages** so the brand becomes associated with its target keywords inside AI
models. **It is not a general SEO tool.**

> **Source of truth:** the *"AI Mention – LLM Query Seeding"* service document.
> **First / pilot client:** [1BillionLinks](https://1billionlinks.com/).

---

## What the service does (the 7 documented steps)

| Step | What | Automated here? |
|------|------|-----------------|
| 1 | Collect inputs (brand, website, 3–7 keywords, niche, package) | ✅ validated from a JSON file |
| 2 | Generate the question set (10 / 25 / 50) | ✅ from the documented templates |
| 3 | Query the LLMs + capture answers/screenshots | ⚙️ **manual**; engine emits a capture template + query plan |
| 4 | Build the master data table (URLs, competitors, frequency, brand appearances) | ✅ from the filled capture file |
| 5 | Build indexing pages (question + AI answer + brand variations + keyword paragraph + URLs + schema + internal links) | ✅ |
| 6 | Fast indexing (sitemap, ping, crawl) | ⚙️ engine emits `sitemap.xml` + a manual checklist |
| 7 | Prepare deliverables (PDF report, CSV table, screenshots, indexing URLs, ZIP) | ✅ |

The engine **never calls an LLM itself** — real model answers and screenshots are supplied via the
capture file (this matches the document's manual "internal team workflow" for STEP 3).

## Packages

| Package | Questions | Models | Indexing pages | Schema |
|---------|-----------|--------|----------------|--------|
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
# PDF + screenshots + links + ZIP)
python -m engine.main run \
  --input inputs/1billionlinks.json \
  --responses inputs/1billionlinks_responses.csv \
  --out outputs

# Seed-only run (STEP 1–3 + previews). Generates the question set and an empty
# capture template to fill manually; pages/tables show "[pending capture]".
python -m engine.main run --input inputs/1billionlinks.json --out outputs
```

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

1. Run **seed-only** → get `outputs/<client>/responses_template.csv` and `query_plan.md`.
2. The delivery team performs **STEP 3** manually: query each in-scope model, paste each answer into
   the `answer` column, list URLs and competitors (pipe `|` separated), and save each screenshot as
   `q{id}_{model}.png`.
3. Run again with `--responses <filled csv>` → full deliverables.

---

## Output (`outputs/<client>/`)

```
questions.csv / questions.json     # STEP 2 question set
responses_template.csv             # STEP 3 capture template (to fill)
query_plan.md                      # STEP 3 manual instructions
master_table.csv                   # STEP 4 master table
source_frequency.csv               # STEP 4 URL frequency
competitor_frequency.csv           # STEP 4 competitor frequency
pages/*.html                       # STEP 5 indexing pages (+ JSON-LD on PRO/ELITE)
sitemap.xml                        # STEP 6
indexing_urls.txt                  # links: created pages
source_links.csv                   # links: extracted source URLs
screenshots/*.png                  # STEP 7 answer-proof images (captured answers)
screenshots/EXPECTED_FILES.txt     # filenames still to capture manually
report.pdf                         # STEP 7 client report
submission_checklist.md            # STEP 6 manual confirmation
manifest.json                      # file inventory
../<client>_deliverable.zip        # STEP 7 ZIP
```

---

## 1BillionLinks pilot

- Input: `inputs/1billionlinks.json` (PRO; keywords/niche/variations grounded in the live site).
- Capture: `inputs/1billionlinks_responses.csv` — the **Claude** column holds genuine Claude answers
  captured 2026-06-28 (see `inputs/1billionlinks_responses.NOTES.md`); ChatGPT/Gemini/Perplexity are
  left for the team. Claude's low recognition of the brand is recorded honestly and *is* the
  "AI understanding gap" the service measures.
- Output: `outputs/1billionlinks/`.

## Assumptions

1. The supplied PDF == the Google Doc (titles/content match; the live Doc is sign-in gated).
2. Engine is offline and deterministic; STEP 3 querying and STEP 6 submission are manual.
3. Competitors are human-entered in the capture file; the engine only counts them. URLs are
   auto-extracted from answers and unioned with any human-entered ones.
4. Brand appearance = literal case-insensitive substring match of the brand + variations.
5. Master table is CSV (the document says "Excel/CSV"); the report is a real PDF; screenshots are PNG
   proof cards for captured answers plus a filename manifest for the manual captures.
6. Indexing-page URLs are the *intended* URLs (`website/slug.html`); actual hosting + index
   submission is performed manually (engine emits the sitemap + checklist).
7. 1BillionLinks keywords/niche/variations were inferred from the website and should be confirmed
   with the client before a paid delivery.

## Out of scope (deliberately not built)

Keyword research, rank tracking, backlink/SEO audits, traffic analytics, CTA/landing pages,
competitor *analysis* beyond counting what the LLM named, dashboards, multi-tenant accounts,
scheduling, or any automated LLM API calls. None of these are in the service document.
