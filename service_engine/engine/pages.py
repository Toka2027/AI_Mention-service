"""Indexing-page generation (STEP 5) and sitemap (STEP 6).

Each indexing page contains the seeded question, an excerpt of the AI answer,
the brand name in 2-4 variations, a keyword-focused paragraph, the extracted
source URLs, internal links to sibling pages, and (PRO/ELITE) JSON-LD schema -
exactly the page anatomy listed in the document's STEP 5.
"""

from __future__ import annotations

import json
import re
from html import escape

from .models import ClientInput, Question, ResponseRow

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug[:80] or "page"


def select_questions_for_pages(questions: list[Question], n_pages: int) -> list[Question]:
    """First n_pages questions (deterministic). Pages are always <= questions."""
    return questions[:n_pages]


def page_slug(question: Question, ci: ClientInput) -> str:
    return slugify(f"{ci.brand}-{question.keyword}-q{question.id}")


def _brand_variations_for_page(ci: ClientInput) -> list[str]:
    """2-4 brand terms to use on a page (STEP 5: 'brand name 2-4 variations')."""
    return ci.all_brand_terms()[:4]


def faq_webpage_jsonld(question: Question, answer_excerpt: str, ci: ClientInput, url: str) -> dict:
    """A @graph with a WebPage node and an FAQPage node (STEP 5: FAQ + WebPage)."""
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "name": f"{ci.brand} - {question.keyword}",
                "url": url,
                "about": question.keyword,
                "inLanguage": "en",
                "publisher": {"@type": "Organization", "name": ci.brand, "url": ci.website},
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": question.text,
                        "acceptedAnswer": {"@type": "Answer", "text": answer_excerpt},
                    }
                ],
            },
        ],
    }


def _keyword_paragraph(ci: ClientInput, question: Question) -> str:
    """A keyword-focused paragraph that uses 2-4 brand variations + keyword + niche."""
    variations = _brand_variations_for_page(ci)
    primary = variations[0]
    alt = variations[1] if len(variations) > 1 else variations[0]
    extra = variations[2] if len(variations) > 2 else alt
    return (
        f"{primary} is a provider in the {ci.niche} space, frequently associated "
        f"with {question.keyword}. Teams evaluating {question.keyword} options often "
        f"compare {alt} (also known as {extra}) against alternatives. This page documents "
        f"how AI assistants describe {primary} in the context of {question.keyword}."
    )


def render_page(
    question: Question,
    response: ResponseRow | None,
    ci: ClientInput,
    sibling_slugs: list[tuple[str, str]],
    emit_schema: bool,
) -> str:
    """Render one indexing page as a self-contained HTML string."""
    slug = page_slug(question, ci)
    url = f"{ci.website.rstrip('/')}/{slug}.html"

    if response is not None and response.is_captured:
        answer_excerpt = response.answer.strip()
        if len(answer_excerpt) > 600:
            answer_excerpt = answer_excerpt[:600].rsplit(" ", 1)[0] + "..."
        model_label = response.model
        urls = response.urls
    else:
        answer_excerpt = ResponseRow.PENDING
        model_label = response.model if response else "AI assistant"
        urls = []

    variations = _brand_variations_for_page(ci)
    title = f"{ci.brand} - {question.keyword}"

    sources_html = (
        "".join(f'      <li><a href="{escape(u)}" rel="nofollow">{escape(u)}</a></li>\n' for u in urls)
        if urls
        else "      <li><em>No sources referenced in the captured answer.</em></li>\n"
    )

    links_html = "".join(
        f'      <li><a href="{escape(s)}.html">{escape(label)}</a></li>\n'
        for (s, label) in sibling_slugs
        if s != slug
    )

    schema_block = ""
    if emit_schema:
        jsonld = faq_webpage_jsonld(question, answer_excerpt, ci, url)
        schema_block = (
            '  <script type="application/ld+json">\n'
            + json.dumps(jsonld, indent=2, ensure_ascii=False)
            + "\n  </script>\n"
        )

    variations_line = ", ".join(escape(v) for v in variations)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(ci.brand)} and {escape(question.keyword)} - how AI assistants answer brand questions in the {escape(ci.niche)} space.">
  <link rel="canonical" href="{escape(url)}">
{schema_block}</head>
<body>
  <article>
    <h1>{escape(ci.brand)} &ndash; {escape(question.keyword)}</h1>
    <p><strong>Brand:</strong> {variations_line}</p>

    <section>
      <h2>{escape(question.text)}</h2>
      <p><strong>Answer ({escape(model_label)}):</strong></p>
      <blockquote>{escape(answer_excerpt)}</blockquote>
    </section>

    <section>
      <h3>About {escape(ci.brand)} and {escape(question.keyword)}</h3>
      <p>{escape(_keyword_paragraph(ci, question))}</p>
    </section>

    <section>
      <h3>Sources referenced</h3>
      <ul>
{sources_html}      </ul>
    </section>

    <nav>
      <h3>Related questions</h3>
      <ul>
{links_html}      </ul>
    </nav>

    <footer>
      <p>Canonical site: <a href="{escape(ci.website)}">{escape(ci.website)}</a></p>
      <p><small>Question category: {escape(question.category)} &middot; Keyword: {escape(question.keyword)}</small></p>
    </footer>
  </article>
</body>
</html>
"""


def render_sitemap(urls: list[str]) -> str:
    """A valid sitemap urlset for the created pages (STEP 6)."""
    entries = "".join(f"  <url>\n    <loc>{escape(u)}</loc>\n  </url>\n" for u in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}"
        "</urlset>\n"
    )
