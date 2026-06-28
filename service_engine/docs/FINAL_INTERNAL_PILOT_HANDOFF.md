# Final Internal Pilot Handoff — AI Mention

Status: **Internal pilot baseline — accepted.** Not public-launch ready.

AI Mention is an **AI Mention / LLM visibility baseline** service. It is **not** a general SEO tool,
ranking tool, or AI-manipulation service.

## What was built
- **Engine** (`service_engine/engine/`): intake validation → brand/niche **question generation** →
  capture template + query plan → **master response table** (URLs, competitors, frequencies, brand
  appearances) → **crawlable support pages** (FAQ + WebPage schema, internal links) → sitemap →
  PDF report + full-page answer-proof images + links + order brief → delivery ZIP.
- **Multi-order isolation**: `outputs/<client-slug>/<order-id>/` + unique per-order ZIP; order brief
  and a responses↔questions mismatch guard (no cross-client mixing).
- **Full-page screenshot SOP**: naming rules, manifest (`EXPECTED_FILES.txt`), documented fallback.
- **QA gate**: `python -m engine.main verify` (artifacts, package/question match, screenshots, intake
  score, client-safe wording scan, cross-client checks).
- **Docs**: client requirements, SEOeStore intake form, operator checklist + runbook, screenshot
  guide, QA gate, hosting workflow (Option C), client-safe notes, readiness + PR checklists, sample
  report.
- **Engineering hygiene**: root `pytest.ini` + `Makefile` + GitHub Actions (`python -m pytest`).

## What was intentionally NOT built (out of scope)
SEO audits, keyword research, rank tracking, traffic analytics, dashboards/UI, automated LLM API
calls, and any hosting implementation. Hosting (Option C) is **documented only**.

## Current readiness
- Internal pilot: **ready**.
- Limited paid orders: **blocked** (operational items below).
- Public launch: **not yet**.

## Exact commands
```bash
# install
cd service_engine && python -m pip install -r requirements.txt

# run the 1BillionLinks order
python -m engine.main run --input inputs/1billionlinks.json \
  --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 --out outputs

# QA gate (non-strict; WARN allowed) and strict (full delivery)
python -m engine.main verify --client-slug 1billionlinks --order-id 2026-06-28-001 --out outputs
python -m engine.main verify --client-slug 1billionlinks --order-id 2026-06-28-001 --strict-screenshots

# tests (any of):
cd service_engine && python -m pytest -q     # canonical
python -m pytest                              # repo root (via pytest.ini)
make test                                     # repo root
```

## Test / CI status
- Local: **28 passed** (root and from `service_engine/`).
- GitHub Actions (`tests` workflow): **passing** (`python -m pytest`).

## 1BillionLinks pilot status
- Order `2026-06-28-001`, PRO package. Output in `outputs/1billionlinks/2026-06-28-001/`.
- Captured: **Claude 25/25** (genuine). Pending (manual): **ChatGPT, Gemini, Perplexity = 75**.
- Non-strict QA: **WARN** (deliverable structure complete; manual screenshots pending).
- Strict QA: **FAIL** until the 75 full-page screenshots are captured (expected; the operational gate).

## Remaining blockers — before limited paid orders
1. **Option C host setup** (SEOeStore subdomain + per-client/order folders); set client `website` to it.
2. **Full all-model 1BillionLinks capture** (ChatGPT + Gemini + Perplexity).
3. **`verify --strict-screenshots` = PASS** on the order.
4. **Pricing / turnaround / scope sign-off** (non-code) + brand-safety sign-off.

## Remaining blockers — before public launch
5. **Report polish** (screenshot thumbnails, per-question table, branded cover).
6. SEOeStore service-page copy locked + customer intake form built.
7. 1–2 delivered paid orders as proof.

## Next operational steps
Stand up the Option C host → capture the 3 pending models (full-page) → paste responses → re-run the
engine → `verify --strict-screenshots` until PASS → deliver. Then address pricing/scope sign-off.
