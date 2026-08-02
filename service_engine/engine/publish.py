"""Publishing / upload layer (configurable, credential-gated).

Turns a finished order folder into a *publish-ready* tree that mirrors exactly what
will sit on one of our own sites, then uploads it once credentials are configured.

Two stages, deliberately separate so missing credentials never block the capture work:

  1. `publish-prepare`  - always runnable. Builds
     outputs/<slug>/<order>_publish/ containing the exact bytes to upload, the
     remote path each file maps to, the final public URL each file will have, and
     a config template naming the credentials still required.

  2. `publish`          - runs once a config file exists. Uploads via the configured
     transport, then writes published_urls.txt + published.json back into the order
     folder so the delivered report carries the real public URLs.

Transports: `local` (copy into a mounted/local web root - needs no credentials),
`sftp` (needs paramiko), and `manual` (prints the exact rsync/scp command to run).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

CONFIG_TEMPLATE = {
    "site": "https://your-site.example",
    "public_base_url": "https://your-site.example/ai-answers",
    "method": "sftp",
    "remote_root": "/var/www/html/ai-answers",
    "host": "",
    "port": 22,
    "username": "",
    "password": "",
    "key_file": "",
    "_comment": (
        "method: sftp | local | manual. For 'local', set remote_root to a local or "
        "mounted web-root path and leave host/username/password empty. Never commit "
        "this file with real credentials - keep it outside the repo."
    ),
}

REQUIRED_BY_METHOD = {
    "sftp": ("host", "username", "remote_root", "public_base_url"),
    "local": ("remote_root", "public_base_url"),
    "manual": ("remote_root", "public_base_url"),
}


@dataclass
class PublishConfig:
    site: str = ""
    public_base_url: str = ""
    method: str = "manual"
    remote_root: str = ""
    host: str = ""
    port: int = 22
    username: str = ""
    password: str = ""
    key_file: str = ""

    @classmethod
    def load(cls, path: str | Path) -> "PublishConfig":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Publish config not found: {p}")
        data = json.loads(p.read_text(encoding="utf-8"))
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    def missing(self) -> list[str]:
        req = REQUIRED_BY_METHOD.get(self.method, REQUIRED_BY_METHOD["manual"])
        return [f for f in req if not str(getattr(self, f, "") or "").strip()]


@dataclass
class PublishPlan:
    """One publish-ready tree: which local file goes where, and its final URL."""
    client_slug: str
    order_id: str
    items: list[dict] = field(default_factory=list)  # {local, remote, url, kind}

    def urls(self, kind: str | None = None) -> list[str]:
        return [i["url"] for i in self.items if kind is None or i["kind"] == kind]


def _remote_prefix(slug: str, oid: str) -> str:
    return f"{slug}/{oid}"


def prepare_publish(
    out_root: str | Path,
    client_slug: str,
    order_id: str,
    public_base_url: str = "",
    include_screenshots: bool = True,
) -> tuple[Path, PublishPlan]:
    """Build the publish-ready folder. Runnable with no credentials at all.

    Layout produced (outputs/<slug>/<order>_publish/):
        public/<slug>/<order>/*.html          support pages
        public/<slug>/<order>/sitemap.xml     sitemap using the final public URLs
        public/<slug>/<order>/proof/*.png     capture screenshots (optional)
        publish_manifest.json                 local -> remote -> public URL
        publish.config.example.json           credentials/config still required
        PUBLISH_README.md                     what to fill in and what to run
    """
    order_dir = Path(out_root) / client_slug / order_id
    if not order_dir.exists():
        raise FileNotFoundError(f"Order folder not found: {order_dir}")

    pub_root = Path(out_root) / client_slug / f"{order_id}_publish"
    if pub_root.exists():
        shutil.rmtree(pub_root)
    prefix = _remote_prefix(client_slug, order_id)
    public_dir = pub_root / "public" / client_slug / order_id
    public_dir.mkdir(parents=True, exist_ok=True)

    base = (public_base_url or "https://REPLACE-WITH-YOUR-SITE").rstrip("/")
    plan = PublishPlan(client_slug=client_slug, order_id=order_id)

    # --- support pages ---
    for src in sorted((order_dir / "pages").glob("*.html")):
        shutil.copyfile(src, public_dir / src.name)
        plan.items.append({
            "local": f"public/{prefix}/{src.name}",
            "remote": f"{prefix}/{src.name}",
            "url": f"{base}/{prefix}/{src.name}",
            "kind": "page",
        })

    # --- proof screenshots (optional asset upload) ---
    if include_screenshots:
        shots = order_dir / "screenshots"
        if shots.exists():
            proof_dir = public_dir / "proof"
            proof_dir.mkdir(exist_ok=True)
            for src in sorted(shots.glob("*.png")):
                shutil.copyfile(src, proof_dir / src.name)
                plan.items.append({
                    "local": f"public/{prefix}/proof/{src.name}",
                    "remote": f"{prefix}/proof/{src.name}",
                    "url": f"{base}/{prefix}/proof/{src.name}",
                    "kind": "screenshot",
                })

    # --- sitemap rebuilt against the FINAL public URLs ---
    page_urls = plan.urls("page")
    sitemap = _render_sitemap(page_urls)
    (public_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    plan.items.append({
        "local": f"public/{prefix}/sitemap.xml",
        "remote": f"{prefix}/sitemap.xml",
        "url": f"{base}/{prefix}/sitemap.xml",
        "kind": "sitemap",
    })

    (pub_root / "publish_manifest.json").write_text(
        json.dumps({
            "client_slug": client_slug,
            "order_id": order_id,
            "public_base_url": base,
            "remote_path_structure": f"<remote_root>/{prefix}/",
            "prepared_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "counts": {
                "pages": len(plan.urls("page")),
                "screenshots": len(plan.urls("screenshot")),
                "sitemap": 1,
            },
            "items": plan.items,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    cfg = dict(CONFIG_TEMPLATE)
    if public_base_url:
        cfg["public_base_url"] = base
    (pub_root / "publish.config.example.json").write_text(
        json.dumps(cfg, indent=2), encoding="utf-8")
    (pub_root / "PUBLISH_README.md").write_text(
        _readme(client_slug, order_id, prefix, base, plan), encoding="utf-8")
    return pub_root, plan


def _render_sitemap(urls: list[str]) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        lines.append(f"  <url><loc>{u}</loc></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def _readme(slug: str, oid: str, prefix: str, base: str, plan: PublishPlan) -> str:
    return f"""# Publish-ready output - {slug} / {oid}

Everything in `public/` is ready to upload as-is.

## Remote path structure

    <remote_root>/{prefix}/*.html         support pages ({len(plan.urls("page"))})
    <remote_root>/{prefix}/sitemap.xml    sitemap
    <remote_root>/{prefix}/proof/*.png    capture screenshots ({len(plan.urls("screenshot"))})

Final public URLs will be `{base}/{prefix}/...` (see publish_manifest.json for the
exact URL of every file).

## Config / credentials still required

Copy `publish.config.example.json` to a file OUTSIDE this repo (it holds secrets),
then fill in:

| field             | meaning                                                  |
|-------------------|----------------------------------------------------------|
| `site`            | which of our sites this order publishes to               |
| `public_base_url` | public URL the remote_root maps to (drives final URLs)   |
| `method`          | `sftp`, `local`, or `manual`                             |
| `remote_root`     | web-root path the files land under                       |
| `host` / `port`   | SFTP host (sftp only)                                    |
| `username`        | SFTP user (sftp only)                                    |
| `password` **or** `key_file` | SFTP auth (sftp only)                         |

## Publish command (once the config exists)

    python -m engine.main publish --client-slug {slug} --order-id {oid} \\
        --config C:/secure/publish.config.json --out outputs

Add `--dry-run` first to print every file, its remote path and its final URL
without uploading anything.
"""


# --- upload transports -------------------------------------------------------

def _upload_local(pub_root: Path, cfg: PublishConfig, plan_items: list[dict]) -> list[str]:
    dest_root = Path(cfg.remote_root)
    done = []
    for item in plan_items:
        src = pub_root / item["local"]
        dst = dest_root / item["remote"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        done.append(item["url"])
    return done


def _upload_sftp(pub_root: Path, cfg: PublishConfig, plan_items: list[dict]) -> list[str]:
    try:
        import paramiko  # type: ignore
    except ImportError as exc:  # noqa: BLE001
        raise RuntimeError(
            "method='sftp' needs paramiko. Install it: python -m pip install paramiko\n"
            "  (or set method='manual' and use the printed rsync/scp command)"
        ) from exc

    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
    ssh.connect(
        hostname=cfg.host, port=cfg.port or 22, username=cfg.username,
        password=cfg.password or None, key_filename=cfg.key_file or None,
    )
    done = []
    try:
        sftp = ssh.open_sftp()
        for item in plan_items:
            remote = f"{cfg.remote_root.rstrip('/')}/{item['remote']}"
            parts = remote.rsplit("/", 1)[0].split("/")
            path = ""
            for part in parts:  # mkdir -p, remote side
                path = f"{path}/{part}" if part else path
                if not path:
                    continue
                try:
                    sftp.stat(path)
                except IOError:
                    sftp.mkdir(path)
            sftp.put(str(pub_root / item["local"]), remote)
            done.append(item["url"])
        sftp.close()
    finally:
        ssh.close()
    return done


def manual_command(pub_root: Path, cfg: PublishConfig) -> str:
    """The exact command to run by hand for method='manual'."""
    src = (pub_root / "public").as_posix().rstrip("/") + "/"
    if cfg.host and cfg.username:
        return (f"rsync -avz --chmod=D755,F644 {src} "
                f"{cfg.username}@{cfg.host}:{cfg.remote_root.rstrip('/')}/")
    return f"rsync -avz --chmod=D755,F644 {src} <user>@<host>:{cfg.remote_root or '<remote_root>'}/"


def publish(
    out_root: str | Path,
    client_slug: str,
    order_id: str,
    config_path: str | Path,
    dry_run: bool = False,
) -> dict:
    """Upload the publish-ready tree and record the resulting public URLs."""
    pub_root = Path(out_root) / client_slug / f"{order_id}_publish"
    manifest_path = pub_root / "publish_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"No publish-ready folder at {pub_root}. Run `publish-prepare` first.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest["items"]
    cfg = PublishConfig.load(config_path)

    missing = cfg.missing()
    if missing:
        raise ValueError(
            f"Publish config is incomplete for method='{cfg.method}'. "
            f"Fill in: {', '.join(missing)} (see {pub_root / 'PUBLISH_README.md'})")

    # Re-point URLs at the configured base in case prepare ran without one.
    base = cfg.public_base_url.rstrip("/")
    for item in items:
        item["url"] = f"{base}/{item['remote']}"

    if dry_run:
        print(f"DRY RUN - method={cfg.method}  remote_root={cfg.remote_root}")
        for item in items:
            print(f"  {item['local']}\n    -> {cfg.remote_root.rstrip('/')}/{item['remote']}"
                  f"\n    => {item['url']}")
        if cfg.method == "manual":
            print(f"\nRun this to publish:\n  {manual_command(pub_root, cfg)}")
        return {"published": [], "dry_run": True, "count": len(items)}

    if cfg.method == "local":
        urls = _upload_local(pub_root, cfg, items)
    elif cfg.method == "sftp":
        urls = _upload_sftp(pub_root, cfg, items)
    elif cfg.method == "manual":
        print("method='manual' - nothing uploaded. Run this command yourself:")
        print(f"  {manual_command(pub_root, cfg)}")
        return {"published": [], "manual_command": manual_command(pub_root, cfg),
                "count": len(items)}
    else:
        raise ValueError(f"Unknown publish method '{cfg.method}' (sftp|local|manual)")

    # Record the real public URLs back into the order folder so the delivered
    # report carries them.
    order_dir = Path(out_root) / client_slug / order_id
    result = {
        "site": cfg.site,
        "public_base_url": base,
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": cfg.method,
        "count": len(urls),
        "urls": urls,
    }
    (order_dir / "published.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (order_dir / "published_urls.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")
    return result
