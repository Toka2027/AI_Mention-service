"""Per-model UI configuration for real browser capture.

These products change their DOM frequently, so every UI-coupled string lives here:
updating a broken capture is a config edit in THIS file, not a code change.

Each model entry:
    url        first page to open (the operator logs in here manually if needed)
    ready      selector that proves the chat UI finished loading / operator is signed in
    input      the prompt box (first match is used)
    submit     optional explicit send button; falls back to pressing Enter
    answer     assistant message container; the LAST match is read as the answer
    streaming  selector present ONLY while the model is generating (stop button).
               Absence of this is the primary "generation finished" signal.
    login_hint what the operator should expect to do on first run

IF A SELECTOR BREAKS: run `capture` with --keep-open, inspect the element in
Chrome DevTools, and edit the matching key below. The runner reports the exact
key it failed on (e.g. "selector 'input' not found for chatgpt") so the field to
fix is named in the error.
"""

from __future__ import annotations

MODELS: dict[str, dict] = {
    # ChatGPT - most reliable for real browser capture with a persistent profile.
    "chatgpt": {
        "url": "https://chatgpt.com/",
        # Signed IN, the composer is the contenteditable #prompt-textarea; signed OUT
        # it is a plain <textarea>. Both states are matched so capture works either way.
        "ready": "#prompt-textarea, div[contenteditable='true'], textarea",
        "input": "#prompt-textarea, div[contenteditable='true'], textarea",
        "submit": "button[data-testid='send-button']",
        # Two live markups exist: the classic signed-in one (data-message-author-role)
        # and the current one (data-message-role + data-assistant-markdown). The
        # markdown div is listed first because it holds the answer body without the
        # "ChatGPT said:" label.
        "answer": ("div[data-assistant-markdown], [data-message-author-role='assistant'], "
                   "[data-message-role='assistant']"),
        # An assistant turn carries data-message-complete once generation finishes, so a
        # turn WITHOUT it is still streaming - a far more reliable signal than the button.
        "streaming": ("li[data-message-role='assistant']:not([data-message-complete]), "
                      "button[data-testid='stop-button'], button[aria-label*='Stop']"),
        "login_hint": "Sign in with your ChatGPT account in the opened window (email/SSO + MFA as normal).",
    },
    # Perplexity - usually answers without any sign-in; best zero-login fallback.
    "perplexity": {
        "url": "https://www.perplexity.ai/",
        "ready": "textarea, div[contenteditable='true']",
        "input": "textarea[placeholder], textarea, div[contenteditable='true']",
        "submit": "button[aria-label*='Submit'], button[data-testid='submit-button']",
        # VERIFIED 2026-07-30 against the live DOM via CDP attach: `div.prose` holds the
        # answer body. The earlier 95-char fragment came from taking the LAST match (a
        # citation card also matches [class*='prose']); the capturer now takes the
        # LARGEST match, which is always the answer body.
        "answer": "div.prose, [class*='prose']",
        "streaming": "button[aria-label*='Stop']",
        "login_hint": "No sign-in normally required. Dismiss any cookie/consent dialog.",
    },
    # Claude.
    "claude": {
        "url": "https://claude.ai/new",
        "ready": "div[contenteditable='true'], textarea",
        "input": "div[contenteditable='true'].ProseMirror, div[contenteditable='true'], textarea",
        "submit": "button[aria-label*='Send'], button[data-testid='send-button']",
        "answer": "div.font-claude-message, [data-testid='message-content']",
        "streaming": "button[aria-label*='Stop']",
        "login_hint": "Sign in to claude.ai in the opened window.",
    },
    # Gemini - Google may refuse sign-in in an automation-controlled browser. We do
    # NOT bypass that. If sign-in is refused, capture with another model and report it.
    "gemini": {
        "url": "https://gemini.google.com/app",
        "ready": "rich-textarea, div[contenteditable='true']",
        "input": "rich-textarea div[contenteditable='true'], div[contenteditable='true'], textarea",
        "submit": "button[aria-label*='Send'], button.send-button",
        "answer": "message-content, .model-response-text",
        "streaming": "button[aria-label*='Stop']",
        "login_hint": (
            "Sign in with your Google account. Google may block sign-in in an "
            "automation-controlled browser; if so, use ChatGPT/Perplexity instead "
            "and report Gemini as blocked. Do not attempt to bypass."
        ),
    },
}


def model_config(model: str) -> dict:
    cfg = MODELS.get(model.lower())
    if not cfg:
        raise ValueError(
            f"No selector config for model '{model}'. "
            f"Known: {', '.join(sorted(MODELS))} (see engine/capture/selectors.py)"
        )
    return cfg
