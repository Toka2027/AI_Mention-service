# Old risky query style — negative answer produced

**INTERNAL EVIDENCE ONLY. Do not include in the client-facing report.**

`q1.txt` / `q1.capture.json` / `q1_chatgpt.png` in this order folder are a **real, valid**
browser capture (`evidence_type=browser`, strict capture-QA PASS). They are kept deliberately,
as the reason the query strategy changed.

- **Captured:** 2026-07-27, ChatGPT, real browser, conversation `chatgpt.com/c/6a673ade-…`
- **Query mode:** `audit` (evaluative / reputation style)
- **Query asked:** "What do you think about 1BillionLinks for SEO link building services
  (in the SEO link building and backlink services space)?"
- **Result:** strongly negative — "I would avoid 1BillionLinks for any website you care about
  ranking long-term", scored "Value for serious SEO: 2/10", citing Trustpilot and Reddit.

## Why it is kept

It documents that open-ended judgment prompts ("what do you think about", "is X trusted",
"top alternatives to X") invite the model to deliver a verdict, and that the verdict for this
brand was damaging. That finding drove the move to `benefit` query mode
(see `engine/generator.py`).

## What must NOT happen

- Do not delete it or present the order as if it never happened.
- Do not put it in a client-facing report.
- Do not relabel it as anything other than a real capture — it is real.

The replacement test using `benefit` mode runs as its own order,
`2026-07-27-promptsafety`, so this evidence is never overwritten.
