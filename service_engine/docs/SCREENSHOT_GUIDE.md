# Full-Page Screenshot Guide (STEP 3)

Screenshots are proof of how each AI tool answered. They must be **full-page**, not cropped.

## Rules
1. **Full page, not partial.** Capture the entire answer from top to bottom.
   - Chrome: DevTools → ⋮ → **Run command** → "Capture full size screenshot".
   - Firefox: right-click → **Take Screenshot** → **Save full page**.
   - Edge: **Web capture** → full page. Or a full-page capture extension (e.g. GoFullPage).
2. **Must be visible in every shot:** the question/prompt, the **complete** answer, and
   **model/interface context** (model name, page title/tab, and the date if shown).
3. **Filename (exact, consistent):** `q{ID}_{model}.png` — lower-case model, no spaces.
   Examples: `q1_chatgpt.png`, `q1_gemini.png`, `q1_perplexity.png`.
   The generated **Claude** proofs already follow this (e.g. `q1_claude.png`).
4. **Readability:** 100% zoom, light theme preferred, no blur. Redact personal data
   (account email, avatar) before saving.
5. **Where to save (IMPORTANT):** the **persistent input** folder
   `inputs/screenshots/<client-slug>/<order-id>/` — NOT the output folder. The engine copies these
   into the delivered `outputs/.../screenshots/` on each run and never overwrites them. The output
   `screenshots/` folder is regenerated (wiped) on every run, so files placed there are lost.
   The exact list of files to provide is in the delivered `screenshots/EXPECTED_FILES.txt` for each order.

## Fallback (when a true full-page capture is not possible)
Some platforms/streamed answers resist single-shot full-page capture. Then:
- Take **2+ overlapping** screenshots covering the whole answer.
- Name them `q{ID}_{model}_part1.png`, `q{ID}_{model}_part2.png`, …
- Record the reason in the capture CSV `behavior_notes` column (e.g. "streamed UI, full-page
  export unavailable — split into 2 parts").

## Models per package
- BASIC: ChatGPT, Gemini
- PRO: ChatGPT, Gemini, Claude, Perplexity
- ELITE: ChatGPT, Gemini, Claude, Perplexity, Llama

> The engine auto-generates a **full-page answer-proof PNG** for any answer captured directly
> (e.g. the pilot's Claude column). All other models require a manual full-page screenshot.
