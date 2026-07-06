"""Real-capture layer for AI Mention.

Operator-assisted browser capture (Playwright + Chrome/Chromium, human-in-the-loop)
that produces REAL answers + REAL full-page screenshots, labelled evidence_type=browser.
Playwright is an OPTIONAL dependency, imported lazily only when a browser capture runs
(`--prepare-only` and prompt-packet writing work without it).

Boundaries: no bypassing login / MFA / CAPTCHA / rate-limits; no stealth. Login is
performed manually by the operator in a persistent browser profile.
"""
