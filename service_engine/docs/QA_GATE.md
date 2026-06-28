# QA Gate — run before sending any deliverable

Every order must pass the QA gate before the ZIP is delivered. There is an **automated** command
and a **manual** fallback. Run the automated gate first; resolve every `[FAIL]` and review every
`[WARN]`.

## Automated (recommended)
```bash
python -m engine.main verify --client-slug <slug> --order-id <order-id> --out outputs
# stricter (treat any missing manual full-page screenshot as a hard fail):
python -m engine.main verify --client-slug <slug> --order-id <order-id> --strict-screenshots
```
- Exit code **0** = no FAIL (PASS or WARN). Exit code **1** = at least one FAIL → **do not deliver**.
- `--min-intake N` sets the acceptable intake completeness (default 8).

### What it checks (maps to the delivery requirements)
| Check | Severity if not met |
|---|---|
| Required artifacts present (order_brief, questions, master_table, report.pdf, sitemap, support_page_urls, source_links, submission_checklist, manifest) | FAIL |
| Support pages exist | FAIL |
| ZIP deliverable exists | FAIL |
| Question count matches package | FAIL |
| Responses (master table) match generated questions | FAIL |
| Intake completeness ≥ threshold | WARN |
| Captured-answer screenshots present | FAIL |
| Manual full-page screenshots present | WARN (FAIL with `--strict-screenshots`) |
| Screenshot naming `q{id}_{model}.png` | WARN |
| Full-page rules + fallback documented | WARN |
| Client-safe wording (no banned promises) | FAIL |
| No cross-client data mixing | FAIL |

The banned-wording scan flags **promises** (e.g. "guarantee AI mentions", "inject signals",
"influence the model", "train the model") in `.md/.txt/.html`. Disclaimers that negate them
("does not guarantee…") are allowed (sentence-scoped negation detection).

## Manual fallback checklist
If you cannot run the command, verify by hand in `outputs/<slug>/<order-id>/`:
- [ ] Required client inputs complete; intake score acceptable (`order_brief.md`).
- [ ] `questions.csv` count matches the package.
- [ ] `master_table.csv` question ids match `questions.csv`.
- [ ] Every captured answer has a screenshot; manual full-page shots present (or fallback noted).
- [ ] Screenshots follow `q{id}_{model}.png`; they are **full-page**.
- [ ] `report.pdf`, `pages/`, `sitemap.xml`, `submission_checklist.md`, ZIP all exist.
- [ ] Read `report.pdf` + a sample page vs `docs/CLIENT_SAFE_NOTES.md` — no banned wording, no guarantees.
- [ ] `order_brief.md` / `manifest.json` show the correct brand + order id (no mixing).

## Policy
- **Block delivery** on any FAIL.
- WARNs are allowed only with an explicit operator note (e.g. "partial-model baseline; remaining
  models scheduled"). For a full delivery, all manual screenshots should be present (use
  `--strict-screenshots`).
