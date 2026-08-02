"""Tests for Chrome session modes (launch-a-profile vs attach-to-operator-Chrome).

The rule that matters most here: in CDP attach mode the engine must NEVER close the
operator's Chrome. That browser holds the human-cleared Cloudflare/MFA session, and
closing it would destroy the only thing that makes blocked models capturable.
"""

from __future__ import annotations

from pathlib import Path

from engine.capture import session
from engine.capture.browser import PlaywrightCapturer


# --- operator Chrome command -------------------------------------------------

def test_chrome_command_uses_a_dedicated_profile_and_port():
    cmd = session.chrome_command("claude", port=9333)
    assert "--remote-debugging-port=9333" in cmd
    # A dedicated --user-data-dir is mandatory: Chrome refuses remote debugging on
    # the default profile, so omitting it would silently fail to open the port.
    assert "--user-data-dir=" in cmd
    assert "chrome-profiles" in cmd and "claude" in cmd
    assert "--disable-blink-features" not in cmd, "no automation-hiding flags"
    assert "stealth" not in cmd.lower()


def test_cdp_and_launch_profiles_are_separate_directories():
    """Attach-mode and launch-mode must not share a profile dir (Chrome locks it)."""
    assert session.cdp_profile_dir("claude") != session.profile_dir("claude")


def test_cdp_is_up_returns_none_when_nothing_is_listening():
    assert session.cdp_is_up("http://127.0.0.1:59999", timeout=1.0) is None


def test_connect_cdp_gives_actionable_error_when_chrome_is_not_running():
    try:
        session.connect_cdp(object(), "http://127.0.0.1:59999")
    except RuntimeError as exc:
        msg = str(exc)
        assert "No Chrome listening" in msg
        assert "--remote-debugging-port" in msg, "the error must show how to fix it"
    else:
        raise AssertionError("attaching to a dead endpoint must raise")


# --- the operator's browser is never closed ----------------------------------

class _FakeBrowser:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeCtx(_FakeBrowser):
    pass


class _FakePw:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


def test_attached_mode_disconnects_but_does_not_close_the_context():
    cap = PlaywrightCapturer("claude", cdp_endpoint="http://127.0.0.1:9222")
    browser, ctx, pw = _FakeBrowser(), _FakeCtx(), _FakePw()
    cap._attached, cap._browser, cap._ctx, cap._pw = True, browser, ctx, pw

    cap.__exit__(None, None, None)

    assert browser.closed is True, "the CDP client should disconnect"
    assert ctx.closed is False, "the operator's context must NOT be closed"
    assert pw.stopped is True


def test_launch_mode_does_close_its_own_context():
    cap = PlaywrightCapturer("claude")
    ctx, pw = _FakeCtx(), _FakePw()
    cap._attached, cap._browser, cap._ctx, cap._pw = False, None, ctx, pw

    cap.__exit__(None, None, None)

    assert ctx.closed is True, "a browser we launched is ours to close"
    assert pw.stopped is True


def test_cdp_endpoint_selects_attach_mode():
    assert PlaywrightCapturer("claude").cdp_endpoint is None
    assert PlaywrightCapturer("claude", cdp_endpoint="http://x:9222").cdp_endpoint
