# Screenshots: what is ready and what is still needed

This engine does NOT claim to upload images and never invents a public image URL.

## Ready now: the by-name bundle

`by-name/` holds 17 folders, each already in the exact shape the API guide's Option 1 expects:

```
by-name/<name>/<name>.txt   documented plain-text content format
by-name/<name>/<name>.png   the real full-page screenshot
```

Upload each folder to the data folder so the files resolve at:

```
https://myqsd.com/dir-ai-data/<name>/<name>.txt
https://myqsd.com/dir-ai-data/<name>/<name>.png
```

Then publish each one with `{"name": "<name>"}` and the page renders WITH its screenshot, and stays live-linked (editing the .txt updates the page).

## What is still missing

The API guide documents how to *reference* files in the data folder but not how to *upload* to it. We need one of:

1. the upload route / credentials for `dir-ai-data/` (SFTP, S3 bucket, admin UI), or
2. any public HTTPS host for these files - the `file` route accepts an allowed-host URL, and `image` accepts an absolute URL.

## Names prepared

- `1billionlinks-q1-chatgpt` — ChatGPT Q1
- `1billionlinks-q2-chatgpt` — ChatGPT Q2
- `1billionlinks-q3-chatgpt` — ChatGPT Q3
- `1billionlinks-q4-chatgpt` — ChatGPT Q4
- `1billionlinks-q5-chatgpt` — ChatGPT Q5
- `1billionlinks-q6-chatgpt` — ChatGPT Q6
- `1billionlinks-q7-chatgpt` — ChatGPT Q7
- `1billionlinks-q8-chatgpt` — ChatGPT Q8
- `1billionlinks-q9-chatgpt` — ChatGPT Q9
- `1billionlinks-q10-chatgpt` — ChatGPT Q10
- `1billionlinks-q1-gemini` — Gemini Q1
- `1billionlinks-q3-gemini` — Gemini Q3
- `1billionlinks-q4-gemini` — Gemini Q4
- `1billionlinks-q6-gemini` — Gemini Q6
- `1billionlinks-q7-gemini` — Gemini Q7
- `1billionlinks-q8-gemini` — Gemini Q8
- `1billionlinks-q9-gemini` — Gemini Q9

Until upload happens, inline-JSON publishing works but the page carries no screenshot; screenshots ship in the delivery ZIP instead.
