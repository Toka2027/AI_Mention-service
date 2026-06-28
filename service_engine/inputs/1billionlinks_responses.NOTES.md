# Capture provenance — 1billionlinks_responses.csv

This file is the **STEP 3 capture** for the 1BillionLinks pilot.

- **Claude** rows: genuine answers from **Claude (Anthropic)**, captured **2026-06-28**
  during the build session. Claude had no specific, independently verified knowledge of
  1BillionLinks; the answers reflect general SEO domain knowledge plus the brand's public
  positioning. That low recognition is recorded honestly — it is itself the "AI understanding
  gap" insight the AI Mention service measures.
- **ChatGPT / Gemini / Perplexity** rows: left as `[pending capture]`. The delivery team
  performs these manually (query each model, paste the answer, list URLs `|`-separated, list
  competitors `|`-separated, save the screenshot named `q{id}_{model}.png`).

To regenerate the master table, pages, report and screenshots after filling more rows, re-run:

```
python -m engine.main run --input inputs/1billionlinks.json \
  --responses inputs/1billionlinks_responses.csv --out outputs
```
