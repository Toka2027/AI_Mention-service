"""AI Mention - AI visibility baseline & LLM query testing engine.

A lightweight, deterministic engine for the documented "AI Mention" micro-service.
It tests how AI tools currently answer brand-focused questions (answers captured
manually), reviews brand/entity associations and visibility gaps, builds crawlable
support pages from the tested questions and findings, and assembles the client
deliverables.

The engine never calls an LLM itself and makes no attempt to inject, train,
manipulate, or guarantee AI answers, mentions, rankings, or indexing. It is an
observational baseline: it documents current AI behaviour, it does not influence it.

Source document: the "AI Mention" service brief.
"""

__version__ = "0.1.0"
