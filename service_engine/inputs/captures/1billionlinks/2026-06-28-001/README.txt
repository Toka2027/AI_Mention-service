Drop raw model ANSWERS here (the engine ingests them - you never edit the CSV).

Layout (one file per question per model; model folder is lower-case):
  chatgpt/q1.txt  chatgpt/q2.txt  ...  chatgpt/q25.txt
  gemini/q1.txt   ...  gemini/q25.txt
  perplexity/q1.txt ... perplexity/q25.txt

Each q{id}.txt = the model's full answer text for that question (from questions.csv).
Optional, per question (same folder): q{id}.urls.txt, q{id}.competitors.txt, q{id}.notes.txt
  (one item per line; the engine also auto-extracts URLs from the answer text).

Screenshots go in a DIFFERENT folder:
  inputs/screenshots/1billionlinks/2026-06-28-001/q{id}_{model}.png   (real full-page browser shots)

Then run ONE command (from service_engine/):
  python -m engine.main deliver --input inputs/1billionlinks.json \
    --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 \
    --out outputs --proof-ok-models Claude

That ingests answers, regenerates the master table / pages / report / screenshots / ZIP,
and runs strict QA. Claude is already captured; you only need ChatGPT, Gemini, Perplexity.
