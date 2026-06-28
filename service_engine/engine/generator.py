"""Question-set generation (STEP 2) and capture-template / query plan (STEP 3).

The question templates are taken verbatim (parameterised) from the document's
"Examples of Brand-Focused Questions" section. Every generated question always
includes a brand mention, a keyword, and a niche clause, as required by STEP 2.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import ClientInput, Question, ResponseRow


@dataclass(frozen=True)
class _Template:
    id: str
    category: str
    text: str  # uses {brand} and {keyword}


# 9 templates across the document's 4 categories.
TEMPLATES: tuple[_Template, ...] = (
    # Direct Brand Questions
    _Template("direct_1", "Direct Brand", "What do you think about {brand} for {keyword} services?"),
    _Template("direct_2", "Direct Brand", "Is {brand} a trusted provider for {keyword}?"),
    _Template("direct_3", "Direct Brand", "How does {brand} compare to other {keyword} companies?"),
    # Keyword + Brand Association
    _Template("assoc_1", "Keyword + Brand", "Which companies offer {keyword}? What about {brand}?"),
    _Template("assoc_2", "Keyword + Brand", "Is {brand} considered an authority for {keyword} solutions?"),
    # Commercial Intent
    _Template("intent_1", "Commercial Intent", "Where can I buy {keyword}? Is {brand} a good option?"),
    _Template("intent_2", "Commercial Intent", "Does {brand} offer fast delivery for {keyword} services?"),
    # Competitive Mapping
    _Template("compete_1", "Competitive Mapping", "Top alternatives to {brand} for {keyword} in 2025."),
    _Template("compete_2", "Competitive Mapping", "What brands compete with {brand} in the {keyword} niche?"),
)

# Niche clauses guarantee STEP 2's "context around the niche" on every question.
# Having 3 variants also makes the (template x keyword x niche) pool large enough
# (>= 3*9*3 = 81) that even ELITE's 50 questions are all unique for any valid
# keyword count (3-7).
NICHE_CLAUSES: tuple[str, str, str] = (
    "(in the {niche} space)",
    "- focused on {niche}",
    "for {niche} clients",
)


def _render_template(tpl: _Template, brand: str, keyword: str, niche_clause: str, niche: str) -> str:
    base = tpl.text.format(brand=brand, keyword=keyword)
    clause = niche_clause.format(niche=niche)
    # Keep punctuation tidy: insert the clause before a trailing '?' / '.'.
    if base.endswith("?") or base.endswith("."):
        return f"{base[:-1]} {clause}{base[-1]}"
    return f"{base} {clause}"


def _candidate_order(n_templates: int, n_keywords: int, n_clauses: int) -> list[tuple[int, int, int]]:
    """Return every (template_idx, keyword_idx, clause_idx) triple, ordered so
    the first picks are diverse (template, keyword and clause all advance each
    step). A deterministic sweep at the end guarantees full, unique coverage
    regardless of how the dimensions divide each other."""
    total = n_templates * n_keywords * n_clauses
    seen: set[tuple[int, int, int]] = set()
    order: list[tuple[int, int, int]] = []

    # Phase 1 - diagonal walk: advancing all three indices keeps consecutive
    # questions varied in category, keyword and niche phrasing.
    i = 0
    max_steps = total * 4
    while len(order) < total and i < max_steps:
        t = i % n_templates
        k = (i + i // n_templates) % n_keywords
        c = (i + i // n_keywords) % n_clauses
        triple = (t, k, c)
        if triple not in seen:
            seen.add(triple)
            order.append(triple)
        i += 1

    # Phase 2 - deterministic backstop: append any triples the walk missed.
    if len(order) < total:
        for t in range(n_templates):
            for k in range(n_keywords):
                for c in range(n_clauses):
                    triple = (t, k, c)
                    if triple not in seen:
                        seen.add(triple)
                        order.append(triple)
    return order


def generate_questions(ci: ClientInput, n: int) -> list[Question]:
    """Generate exactly ``n`` unique questions for the client."""
    keywords = ci.keywords
    questions: list[Question] = []
    for (t, k, c) in _candidate_order(len(TEMPLATES), len(keywords), len(NICHE_CLAUSES)):
        if len(questions) >= n:
            break
        tpl = TEMPLATES[t]
        kw = keywords[k]
        text = _render_template(tpl, ci.brand, kw, NICHE_CLAUSES[c], ci.niche)
        questions.append(
            Question(
                id=len(questions) + 1,
                text=text,
                template_id=tpl.id,
                category=tpl.category,
                keyword=kw,
            )
        )
    return questions


def build_capture_template(questions: list[Question], models: tuple[str, ...]) -> list[ResponseRow]:
    """One blank row per (question x model) for the team to fill (STEP 3)."""
    rows: list[ResponseRow] = []
    for q in questions:
        for model in models:
            rows.append(
                ResponseRow(
                    question_id=q.id,
                    model=model,
                    answer=ResponseRow.PENDING,
                    screenshot_filename=f"q{q.id}_{model.lower()}.png",
                )
            )
    return rows


def build_query_plan(ci: ClientInput, questions: list[Question], models: tuple[str, ...]) -> str:
    """Human-readable instructions for the manual STEP 3."""
    lines: list[str] = []
    lines.append(f"# Query Plan - {ci.brand} ({ci.package})")
    lines.append("")
    lines.append("STEP 3 of the AI Mention workflow is performed manually by the delivery team.")
    lines.append("Ask every question below on each of these models and capture the result:")
    lines.append("")
    lines.append(f"- Models in scope ({ci.package}): {', '.join(models)}")
    lines.append(f"- Total questions: {len(questions)}")
    lines.append(f"- Total captures to collect: {len(questions) * len(models)} (questions x models)")
    lines.append("")
    lines.append("For each answer:")
    lines.append("  1. Save a screenshot as `screenshots/q{ID}_{model}.png` (lower-case model).")
    lines.append("  2. Paste the answer text into `responses_template.csv` (column `answer`).")
    lines.append("  3. List any URLs the model gave in `urls` (pipe `|` separated).")
    lines.append("  4. List any competitor brands the model named in `competitors` (pipe `|` separated).")
    lines.append("  5. Note behaviour patterns in `behavior_notes`.")
    lines.append("")
    lines.append("Questions:")
    for q in questions:
        lines.append(f"  Q{q.id} [{q.category} / {q.keyword}] {q.text}")
    lines.append("")
    return "\n".join(lines)
