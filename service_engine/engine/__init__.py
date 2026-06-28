"""AI Mention - LLM Query Seeding engine.

A lightweight, deterministic engine that implements the documented "AI Mention"
micro-service: it seeds brand-focused questions into LLMs (manual capture step),
turns the captured answers into crawlable indexing pages, and assembles the
client deliverables. The engine never calls an LLM itself.

Source of truth: the "AI Mention - LLM Query Seeding" service document.
"""

__version__ = "0.1.0"
