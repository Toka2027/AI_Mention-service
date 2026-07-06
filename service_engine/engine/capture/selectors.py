"""Per-model UI configuration for browser capture.

URLs and DOM selectors change frequently on these products; keep them here so an
update is a config edit, not a code change. These are best-effort starting points —
the operator should verify/tune them in their environment. `done` is a best-effort
"generation finished" signal; capture also uses an operator-confirm prompt, so it is
robust even if `done` is stale.
"""

from __future__ import annotations

MODELS: dict[str, dict] = {
    "chatgpt": {
        "url": "https://chatgpt.com/",
        "input": "div[contenteditable='true'], #prompt-textarea, textarea",
        "answer": "div[data-message-author-role='assistant']",
        "done": "button[data-testid='send-button']:not([disabled])",
    },
    "gemini": {
        "url": "https://gemini.google.com/app",
        "input": "div[contenteditable='true'], rich-textarea textarea, textarea",
        "answer": "message-content, .model-response-text",
        "done": "",
    },
    "perplexity": {
        "url": "https://www.perplexity.ai/",
        "input": "textarea, div[contenteditable='true']",
        "answer": "div.prose, [class*='answer']",
        "done": "",
    },
    "claude": {
        "url": "https://claude.ai/new",
        "input": "div[contenteditable='true'], textarea",
        "answer": "div.font-claude-message, [data-testid='message-content']",
        "done": "",
    },
}
