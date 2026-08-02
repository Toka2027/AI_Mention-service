"""S3-compatible object storage upload for proof screenshots.

Reuses the object-storage account already configured for the captcharank project
(Hetzner Object Storage, S3-compatible). Credentials are NEVER copied into this repo:
the config file is located by the AIMENTION_S3_CONFIG environment variable, falling
back to the known reference path. Nothing here prints or logs a key.

Config file shape (same as the existing captcharank config):
    {
      "endpoint":        "https://<bucket>.<region>.your-objectstorage.com",
      "bucket":          "<bucket>",
      "region":          "<region>",
      "access_key":      "<secret>",
      "secret_key":      "<secret>",
      "prefix":          "captcharank/blog",
      "public_url_base": "https://<bucket>.<region>.your-objectstorage.com/<prefix>"
    }

AI Mention writes under its OWN prefix so it can never overwrite blog assets:
    <AIMENTION_PREFIX>/<client-slug>/<order-id>/<file>.png
"""

from __future__ import annotations

import csv
import json
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

CONFIG_ENV = "AIMENTION_S3_CONFIG"
DEFAULT_CONFIG_PATH = Path(r"C:\git\captcharank_content\reference\hetzner_object_storage.json")
AIMENTION_PREFIX = "ai-mention"

SECRET_FIELDS = ("access_key", "secret_key")
REQUIRED_FIELDS = ("bucket", "region", "access_key", "secret_key")

UPLOAD_COLS = ["query_id", "model", "local_screenshot_path", "s3_key",
               "public_image_url", "uploaded_at", "safe_to_share"]


def config_path() -> Path:
    """Where the storage config lives (env var wins, else the reference path)."""
    env = (os.environ.get(CONFIG_ENV) or "").strip()
    return Path(env) if env else DEFAULT_CONFIG_PATH


def load_config() -> dict:
    """Load the storage config. Raises with an actionable message when unusable."""
    p = config_path()
    if not p.exists():
        raise FileNotFoundError(
            f"Object-storage config not found: {p}\n"
            f"  Set {CONFIG_ENV} to a JSON file containing: "
            f"{', '.join(REQUIRED_FIELDS)} (+ optional prefix/public_url_base).\n"
            f"  Keep that file OUTSIDE this repo - it holds credentials."
        )
    cfg = json.loads(p.read_text(encoding="utf-8"))
    missing = [f for f in REQUIRED_FIELDS if not str(cfg.get(f, "")).strip()]
    if missing:
        raise ValueError(f"Object-storage config {p} is missing: {', '.join(missing)}")
    return cfg


def safe_config_summary(cfg: dict | None = None) -> dict:
    """Config with every secret masked - safe to print or write to a manifest."""
    cfg = cfg or load_config()
    out = {}
    for k, v in cfg.items():
        s = str(v)
        out[k] = (f"{s[:4]}...{s[-2:]} (masked, len={len(s)})"
                  if k in SECRET_FIELDS else s)
    out["_config_path"] = str(config_path())
    return out


def public_root(cfg: dict) -> str:
    """Public HTTPS root that object keys hang off.

    Prefers an explicit `public_root`. Otherwise derives the bucket-subdomain form,
    which is what this account already serves (`public_url_base` is that root plus the
    captcharank prefix, so it cannot be reused for our prefix directly).
    """
    if cfg.get("public_root"):
        return str(cfg["public_root"]).rstrip("/")
    endpoint = str(cfg.get("endpoint") or "").rstrip("/")
    bucket = str(cfg["bucket"])
    if endpoint and bucket in urlparse(endpoint).netloc:
        return endpoint
    base = str(cfg.get("public_url_base") or "").rstrip("/")
    prefix = str(cfg.get("prefix") or "").strip("/")
    if base and prefix and base.endswith("/" + prefix):
        return base[: -(len(prefix) + 1)]
    if endpoint:
        u = urlparse(endpoint)
        return f"{u.scheme}://{bucket}.{u.netloc}"
    return f"https://{bucket}.{cfg['region']}.your-objectstorage.com"


def object_key(client_slug: str, order_id: str, filename: str,
               prefix: str = AIMENTION_PREFIX) -> str:
    return f"{prefix.strip('/')}/{client_slug}/{order_id}/{filename}"


def public_url(key: str, cfg: dict | None = None) -> str:
    return f"{public_root(cfg or load_config())}/{key.lstrip('/')}"


def _client(cfg: dict):
    import boto3  # lazy: only needed when actually uploading

    # The account's API endpoint is region-scoped (bucket is passed per call).
    return boto3.client(
        "s3",
        endpoint_url=f"https://{cfg['region']}.your-objectstorage.com",
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret_key"],
    )


def upload_screenshots(
    items: list[dict],
    client_slug: str,
    order_id: str,
    prefix: str = AIMENTION_PREFIX,
    dry_run: bool = False,
) -> list[dict]:
    """Upload each item's screenshot and return rows with its public URL.

    `items` entries need: query_id, model, screenshot_path, safe_to_share.
    ONLY items marked safe are uploaded - an unsafe capture must never become a
    public asset. Failures are recorded per row; nothing is invented.
    """
    cfg = load_config()
    rows: list[dict] = []
    client = None if dry_run else _client(cfg)

    for it in items:
        src = Path(it["screenshot_path"])
        safe = str(it.get("safe_to_share", "")).lower() in ("yes", "true", "1")
        row = {
            "query_id": it["query_id"], "model": it["model"],
            "local_screenshot_path": src.as_posix(), "s3_key": "",
            "public_image_url": "", "uploaded_at": "",
            "safe_to_share": "yes" if safe else "no",
        }
        if not safe:
            row["uploaded_at"] = "SKIPPED (not client-safe)"
            rows.append(row)
            continue
        if not src.exists():
            row["uploaded_at"] = f"FAILED (missing file: {src})"
            rows.append(row)
            continue

        key = object_key(client_slug, order_id, src.name, prefix)
        url = public_url(key, cfg)
        row["s3_key"] = key
        if dry_run:
            row["public_image_url"] = url
            row["uploaded_at"] = "DRY RUN"
            rows.append(row)
            continue
        try:
            ctype = mimetypes.guess_type(str(src))[0] or "image/png"
            client.upload_file(
                str(src), cfg["bucket"], key,
                ExtraArgs={"ContentType": ctype, "ACL": "public-read"},
            )
            row["public_image_url"] = url
            row["uploaded_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        except Exception as exc:  # noqa: BLE001 - record, never fabricate a URL
            row["uploaded_at"] = f"FAILED ({type(exc).__name__}: {str(exc)[:120]})"
        rows.append(row)
    return rows


def write_upload_csv(rows: list[dict], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=UPLOAD_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in UPLOAD_COLS})
    return p


def verify_public(url: str, timeout: int = 25) -> tuple[bool, str]:
    """Confirm an uploaded object is actually reachable over public HTTPS."""
    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request(url, method="GET", headers={"Range": "bytes=0-7"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            head = r.read(8)
            ok = r.status in (200, 206) and head.startswith(b"\x89PNG\r\n\x1a\n")
            return ok, f"HTTP {r.status}" + ("" if ok else " (not a PNG body)")
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}"
