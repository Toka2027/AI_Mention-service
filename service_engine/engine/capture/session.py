"""Persistent browser profile + Chrome resolution for real browser capture.

The operator signs in manually the first time; the session (cookies/localStorage)
persists in a per-model profile directory for subsequent runs. The engine stores
NO credentials, and nothing about the login is automated or bypassed.

Browser choice: we prefer the operator's real installed Chrome (Playwright
`channel="chrome"`) and fall back to Playwright's bundled Chromium. We deliberately
do NOT apply stealth flags or anti-detection patches.
"""

from __future__ import annotations

import shutil
from pathlib import Path

SESSIONS_ROOT = Path.home() / ".aimention" / "sessions"


def profile_dir(model: str) -> Path:
    """Persistent profile dir for one model (created on first use)."""
    d = SESSIONS_ROOT / model.lower()
    d.mkdir(parents=True, exist_ok=True)
    return d


def chrome_available() -> bool:
    """True when a real Google Chrome install is discoverable for `channel='chrome'`."""
    if shutil.which("chrome") or shutil.which("google-chrome"):
        return True
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/usr/bin/google-chrome"),
    ]
    return any(p.exists() for p in candidates)


def chrome_exe() -> str | None:
    """Path to the installed Google Chrome, if we can find it."""
    for p in (shutil.which("chrome"), shutil.which("google-chrome")):
        if p:
            return p
    for c in (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/usr/bin/google-chrome"),
    ):
        if c.exists():
            return str(c)
    return None


def cdp_profile_dir(model: str, create: bool = True) -> Path:
    """Profile dir for operator-started Chrome (kept apart from launch-mode profiles).

    `create=False` when the path is only being formatted into a message - building an
    error string must not have filesystem side effects (and a placeholder model name
    is not a legal directory name on Windows).
    """
    d = Path.home() / ".aimention" / "chrome-profiles" / model.lower()
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def chrome_command(model: str, port: int = 9222, create_profile: bool = True) -> str:
    """The exact command the operator runs to start their own Chrome for CDP attach.

    A dedicated --user-data-dir is REQUIRED: current Chrome refuses
    --remote-debugging-port on the default profile. The operator signs in once in this
    profile and it persists.
    """
    exe = chrome_exe() or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    profile = cdp_profile_dir(model, create=create_profile)
    return f'"{exe}" --remote-debugging-port={port} --user-data-dir="{profile}"'


def cdp_is_up(endpoint: str, timeout: float = 3.0) -> dict | None:
    """Probe a CDP endpoint's /json/version. Returns the payload or None."""
    import json as _json
    import urllib.request

    base = endpoint.rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/json/version", timeout=timeout) as r:
            return _json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001 - not running / wrong port
        return None


def connect_cdp(pw, endpoint: str):
    """Attach to a Chrome the OPERATOR started. Returns (context, label, browser).

    The browser process is not ours: it carries no automation flags, and whatever the
    operator already cleared by hand (Cloudflare, sign-in, MFA) is simply still in
    effect. We must never close it - see PlaywrightCapturer.__exit__.
    """
    info = cdp_is_up(endpoint)
    if info is None:
        exe = chrome_exe() or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        port = endpoint.rsplit(":", 1)[-1].strip("/") or "9222"
        raise RuntimeError(
            f"No Chrome listening on {endpoint}.\n"
            f"  Start it first (see: engine.main chrome-start --model <model>):\n"
            f'    "{exe}" --remote-debugging-port={port} '
            f'--user-data-dir="{Path.home() / ".aimention" / "chrome-profiles" / "<model>"}"\n'
            f"  A dedicated --user-data-dir is required; Chrome refuses remote "
            f"debugging on the default profile."
        )
    browser = pw.chromium.connect_over_cdp(endpoint)
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    return ctx, f"chrome-cdp ({info.get('Browser', 'unknown')})", browser


def launch_context(pw, model: str, headful: bool = True, prefer_chrome: bool = True):
    """Launch a persistent Chrome/Chromium context for `model`.

    Returns (context, browser_label). Tries real Chrome first so the operator gets
    the same browser (and sign-in experience) they normally use, then falls back to
    Playwright's bundled Chromium.
    """
    args = {
        "user_data_dir": str(profile_dir(model)),
        "headless": not headful,
        "viewport": {"width": 1440, "height": 900},
        "accept_downloads": False,
    }
    if prefer_chrome and chrome_available():
        try:
            return pw.chromium.launch_persistent_context(channel="chrome", **args), "chrome"
        except Exception:  # noqa: BLE001 - fall back to bundled Chromium
            pass
    return pw.chromium.launch_persistent_context(**args), "chromium"


# Text that only appears when you are NOT signed in to a given product. Checked
# against the page body to tell "signed in" from "signed out but reachable".
SIGNED_OUT_MARKERS: dict[str, tuple[str, ...]] = {
    "chatgpt": ("Log in", "Sign up for free"),
    "gemini": ("Sign in",),
    "claude": ("Sign in", "Continue with"),
    "perplexity": ("Sign In", "Sign in"),
}


def session_status(cdp_endpoint: str, models: list[str]) -> list[dict]:
    """Per-model readiness in the attached Chrome: reachable, signed in, capture-ready.

    Run this BEFORE a long capture: it turns "two hours in, model 3 was never signed
    in" into a five-second check.
    """
    from playwright.sync_api import sync_playwright  # lazy

    from .selectors import model_config

    rows: list[dict] = []
    with sync_playwright() as pw:
        ctx, _label, browser = connect_cdp(pw, cdp_endpoint)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for model in models:
            try:
                cfg = model_config(model)
            except ValueError as exc:
                rows.append({"model": model, "reachable": False, "signed_in": False,
                             "ready": False, "detail": str(exc)})
                continue
            try:
                page.goto(cfg["url"], wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(7000)
                title = (page.title() or "")
                body = (page.locator("body").inner_text() or "")
                challenged = ("just a moment" in title.lower()
                              or "verifying you are human" in body.lower()
                              or "security verification" in body.lower())
                has_input = page.locator(cfg["ready"]).count() > 0
                signed_out = any(m in body for m in SIGNED_OUT_MARKERS.get(model.lower(), ()))
                if challenged:
                    detail = "bot-verification page showing - clear it by hand in Chrome"
                    rows.append({"model": model, "reachable": False, "signed_in": False,
                                 "ready": False, "detail": detail})
                else:
                    ready = has_input and not signed_out
                    detail = (f"signed in, chat input present ({title[:32]})" if ready
                              else f"reachable but signed out ({title[:32]})" if has_input
                              else f"chat input not found ({title[:32]})")
                    rows.append({"model": model, "reachable": True,
                                 "signed_in": not signed_out, "ready": ready,
                                 "detail": detail})
            except Exception as exc:  # noqa: BLE001
                rows.append({"model": model, "reachable": False, "signed_in": False,
                             "ready": False, "detail": f"{type(exc).__name__}: {exc}"[:70]})
        browser.close()  # detach only - the operator's Chrome keeps running
    return rows


def open_login(model: str, headful: bool = True, cdp_endpoint: str | None = None) -> int:
    """Verify that the model's chat UI is reachable and ready for capture.

    Launch mode  : opens the persistent profile so the operator can sign in, then
                   closes the browser, leaving the session stored for later runs.
    CDP mode     : attaches to the Chrome the operator started, checks the chat UI is
                   usable, and LEAVES THAT CHROME RUNNING (it holds the human-cleared
                   session). Nothing is bypassed and no login is automated.
    """
    from playwright.sync_api import sync_playwright  # lazy

    from .selectors import model_config

    cfg = model_config(model)
    with sync_playwright() as pw:
        if cdp_endpoint:
            ctx, label, browser = connect_cdp(pw, cdp_endpoint)
            print(f"[{model}] attached to {label}")
            host = cfg["url"].split("/")[2]
            page = next((p for p in ctx.pages if host in p.url), None)
            if page is None:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
            if host not in page.url:
                page.goto(cfg["url"], wait_until="domcontentloaded")
        else:
            ctx, label = launch_context(pw, model, headful=headful)
            browser = None
            print(f"[{model}] browser: {label}  profile: {profile_dir(model)}")
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(cfg["url"], wait_until="domcontentloaded")

        print(f"[{model}] {cfg['login_hint']}")
        input(f"[{model}] Sign in / clear any verification in the browser, "
              f"then press Enter here...")
        try:
            page.wait_for_selector(cfg["ready"], timeout=10000)
            signed_in = True
        except Exception:  # noqa: BLE001
            signed_in = False
        title = (page.title() or "")
        url = page.url
        if browser is not None:
            browser.close()   # detach only - the operator's Chrome keeps running
        else:
            ctx.close()

    print(f"[{model}] page: {title[:50]!r}  url: {url[:70]}")
    if not signed_in:
        print(f"[{model}] NOT READY: the chat input is not visible. Either sign-in is "
              f"incomplete, a verification page is still showing, or the 'ready' "
              f"selector needs updating in engine/capture/selectors.py")
        return 1
    print(f"[{model}] READY for capture.")
    return 0
