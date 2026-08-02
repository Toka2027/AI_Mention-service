# Publishing / Upload Layer

Takes a finished order folder and puts the support pages, sitemap, and proof assets onto one of our
own sites, then records the real public URLs back into the delivered report.

Two stages, deliberately separate so **missing credentials never block capture or delivery**.

## I. Prepare the publish-ready folder (no credentials needed)
```
python -m engine.main publish-prepare --client-slug 1billionlinks --order-id 2026-06-28-001 \
  --out outputs --public-base-url https://oursite.com/ai-answers
```
Builds `outputs/<slug>/<order>_publish/`:
```
public/<slug>/<order>/*.html         support pages, exactly as they will be served
public/<slug>/<order>/sitemap.xml    sitemap rebuilt against the FINAL public URLs
public/<slug>/<order>/proof/*.png    capture screenshots (omit with --no-screenshots)
publish_manifest.json                every file: local path -> remote path -> public URL
publish.config.example.json          the config/credentials template to fill in
PUBLISH_README.md                    what to fill in and what to run
```
Remote path structure is `<remote_root>/<client-slug>/<order-id>/...`, so orders and clients never
collide on the server.

## J. Publish once credentials exist
```
# see exactly what would go where, upload nothing
python -m engine.main publish --client-slug 1billionlinks --order-id 2026-06-28-001 \
  --out outputs --config C:/secure/publish.config.json --dry-run

# real upload
python -m engine.main publish --client-slug 1billionlinks --order-id 2026-06-28-001 \
  --out outputs --config C:/secure/publish.config.json
```
On success it writes `published_urls.txt` and `published.json` into the order folder, so the
delivered package carries the real public URLs.

## Config file
Keep this **outside the repo** — it holds secrets.
```json
{
  "site": "https://oursite.com",
  "public_base_url": "https://oursite.com/ai-answers",
  "method": "sftp",
  "remote_root": "/var/www/html/ai-answers",
  "host": "sftp.oursite.com",
  "port": 22,
  "username": "deploy",
  "password": "",
  "key_file": "C:/Users/you/.ssh/id_ed25519"
}
```

| field | required for | meaning |
|---|---|---|
| `site` | all | which of our sites this order publishes to |
| `public_base_url` | all | public URL that `remote_root` maps to — drives the final URLs |
| `method` | all | `sftp`, `local`, or `manual` |
| `remote_root` | all | web-root path the files land under |
| `host`, `port` | sftp | SFTP server |
| `username` | sftp | SFTP user |
| `password` **or** `key_file` | sftp | SFTP auth (key preferred) |

`publish` refuses to run with an incomplete config and names the missing fields.

## Transports
| method | needs | use when |
|---|---|---|
| `local` | nothing | the web root is a local or mounted path |
| `sftp` | `python -m pip install paramiko` | normal remote hosting |
| `manual` | nothing | you want the exact `rsync` command and will run it yourself |

`manual` prints a ready-to-run command, e.g.
```
rsync -avz --chmod=D755,F644 outputs/1billionlinks/2026-06-28-001_publish/public/ \
  deploy@sftp.oursite.com:/var/www/html/ai-answers/
```

## What is needed to go live
1. Which of our sites hosts these pages (domain + web root path).
2. Upload access to it: SFTP host/user/key, or a mounted path for `method: "local"`.
3. The public base URL that maps to that web root.

Until those exist, `publish-prepare` still runs and the publish-ready folder is complete — only the
final upload waits.

---

# Directory Article API (myqsd.com)

Publishes one page per captured answer via inline JSON — no separate content-file upload.

## Authentication

The key is read **only** from the `DIR_AI_API_KEY` environment variable and sent as the
`X-Dir-Ai-Api-Key` header. It is never hardcoded, never written to a payload or manifest,
and never logged.

```powershell
$env:DIR_AI_API_KEY = '<key>'      # PowerShell
```
```bash
export DIR_AI_API_KEY='<key>'      # bash
```

## Commands

```
# A) build one payload per capture (safe ones only); no key needed
python -m engine.main publish-prepare --input inputs/1billionlinks.json \
  --order-id 2026-06-28-001 --models chatgpt,gemini --questions 1-10 --safe-only

# B) publish (add --dry-run first to see exactly what would be sent)
python -m engine.main publish --input inputs/1billionlinks.json \
  --order-id 2026-06-28-001 --models chatgpt,gemini --questions 1-10 --safe-only

# D) build the scoped 2-model delivery (internal + client reports + ZIP)
python -m engine.main deliver --input inputs/1billionlinks.json \
  --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 --out outputs \
  --require-evidence ChatGPT,Gemini --scope two-model --models chatgpt,gemini --questions 1-10
```

C) Public URLs are written to `outputs/<slug>/<order>/published_urls.csv`
(`query_id, model, public_url, safe_to_share, screenshot_path, answer_path`).

## Payload shape — verified against the live contract

`GET https://myqsd.com/api/dir-ai-order.php` returns the API's own self-description.
Conversation messages use **`text`**, not `content` — publishing with `content` alone
renders an empty conversation. We emit both. The success response returns `link`.

## Screenshots are NOT uploaded by this API

The documented routes cover article payloads (`inline`, `file`, `name`). There is no
documented raw-image upload endpoint, so the engine references screenshots by **local
path** in `metadata.screenshot_path` and stages the files under
`outputs/<slug>/<order>/publish/screenshots-to-host/` with a `SCREENSHOT_HOSTING.md`
note. No public image URL is ever invented.

To make them public, either give us the `{image_base}` write location behind the
documented `create_order_by_name` route (`{data_base}/{name}.txt` +
`{image_base}/{name}.png`), or host the staged folder anywhere and give us the base URL.
