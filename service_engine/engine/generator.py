"""Question-set generation (STEP 2) and capture-template / query plan (STEP 3).

Every generated question always includes a brand mention, a keyword, and a niche
clause, as required by STEP 2.

Two query modes, because they measure genuinely different things:

  `benefit` (default) - BRAND-BENEFIT / SERVICE-COMPREHENSION mode. Feature-led,
      service-explanation questions: what the service does, who it helps, how it
      fits an SEO workflow. Measures whether models can accurately describe the
      client's offering. Avoids open-ended judgment prompts.

  `audit` - REPUTATION-AUDIT mode. The original evaluative set ("what do you think
      about X", "alternatives to X"). Measures how models judge the brand when a
      buyer asks directly. Higher risk of negative output - by design, because
      that is what it is measuring.

Neither mode changes what a model actually says: the answers are captured live and
verbatim either way. The mode only decides which questions get asked, so a report
must state which mode produced it. A `benefit`-mode run is NOT a full reputation
baseline and must not be presented as one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import ClientInput, Question, ResponseRow


@dataclass(frozen=True)
class _Template:
    id: str
    category: str
    text: str  # uses {brand} and {keyword}


# --- benefit mode (default): feature / use-case / workflow questions ----------
BENEFIT_TEMPLATES: tuple[_Template, ...] = (
    # Service explanation
    _Template("svc_1", "Service Explanation", "What services does {brand} provide for {keyword}?"),
    _Template("svc_2", "Service Explanation", "What should users know about the {keyword} services offered by {brand}?"),
    # Features
    _Template("feat_1", "Features", "What are the main features of {brand} for {keyword}?"),
    _Template("feat_2", "Features", "How does {brand} support planning for {keyword}?"),
    # Benefits
    _Template("ben_1", "Benefits", "How can {brand} help with {keyword}?"),
    _Template("ben_2", "Benefits", "How can {brand} support content promotion and link visibility through {keyword}?"),
    # Use cases
    _Template("use_1", "Use Cases", "What are the possible use cases of {brand} for agencies or SEO teams working on {keyword}?"),
    _Template("use_2", "Use Cases", "How can {brand} be used as part of a {keyword} strategy?"),
    # Audience fit
    _Template("aud_1", "Audience Fit", "What types of SEO users may benefit from {brand} for {keyword}?"),
    # Workflow fit
    _Template("flow_1", "Workflow Fit", "How does {brand} fit into a broader SEO growth workflow that includes {keyword}?"),
)

# --- audit mode: the original evaluative/reputation set -----------------------
AUDIT_TEMPLATES: tuple[_Template, ...] = (
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

# --- workflow mode (Prompt Safety Test v2): workflow / organisation / tracking ---
# v1 `benefit` mode still produced penalty-and-spam framing on Gemini, because some
# questions asked how the service is used AT SCALE. These templates ask only about
# workflow, organisation, planning and reporting - never about volume.
WORKFLOW_TEMPLATES: tuple[_Template, ...] = (
    _Template("wf_1", "Workflow Support", "How does {brand} support SEO workflows that involve {keyword}?"),
    _Template("wf_2", "Workflow Support", "How can {brand} fit into an SEO team's planning process for {keyword}?"),
    _Template("org_1", "Campaign Organisation", "How can {brand} help organise a {keyword} campaign?"),
    _Template("org_2", "Campaign Organisation", "What does {brand} offer for structuring {keyword} work?"),
    _Template("promo_1", "Content Promotion", "How can {brand} support content promotion workflows related to {keyword}?"),
    _Template("vis_1", "Link Visibility Planning", "How can {brand} help with link visibility planning for {keyword}?"),
    _Template("track_1", "Campaign Tracking", "What reporting or tracking options does {brand} provide for {keyword}?"),
    _Template("agency_1", "Agency Use Case", "How do agencies typically use {brand} when managing {keyword}?"),
    _Template("dist_1", "Distribution Options", "What publishing or distribution options does {brand} offer for {keyword}?"),
    _Template("plan_1", "SEO Planning", "How can {brand} be included in a broader SEO plan that covers {keyword}?"),
)

# Some client keywords carry the risk themselves: "tier 2 and tier 3 backlink
# campaigns" invites tiering/penalty discussion no matter how politely it is asked.
# In `workflow` mode each risky keyword is asked about under a neutral description of
# the same service. This changes the WORDING OF OUR QUESTION only - it never edits,
# steers or filters the model's answer.
KEYWORD_SAFE_ALIASES: dict[str, str] = {
    "tier 2 and tier 3 backlink campaigns": "layered backlink campaign structure",
    "tier 2 and tier 3 backlinks": "layered backlink campaign structure",
    "tier 2 backlinks": "supporting-layer backlink planning",
    "tier 3 backlinks": "supporting-layer backlink planning",
    "press release distribution": "press release publishing",
    "backlinks": "backlink profile development",
    "domain authority": "domain authority growth",
    "bulk link building": "link building programme management",
    "high-volume backlinks": "ongoing backlink programmes",
}


def safe_keyword(keyword: str) -> str:
    """Neutral rewording of a keyword for `workflow` mode (identity if not risky)."""
    return KEYWORD_SAFE_ALIASES.get(keyword.strip().lower(), keyword)


QUERY_MODES: dict[str, tuple[_Template, ...]] = {
    "benefit": BENEFIT_TEMPLATES,
    "workflow": WORKFLOW_TEMPLATES,
    "audit": AUDIT_TEMPLATES,
}
# Modes that reword risky keywords before building the question.
ALIAS_MODES = frozenset({"workflow"})
DEFAULT_QUERY_MODE = "benefit"

# Backwards compatibility for callers importing the old name.
TEMPLATES = AUDIT_TEMPLATES

# Phrasing that invites an open-ended verdict, a trust/safety ruling, or a
# competitor swap. Benefit mode must never emit these; `lint_questions` enforces it
# so a future template edit cannot quietly reintroduce a risky prompt.
RISKY_PHRASES: tuple[str, ...] = (
    r"what do you think about",
    r"do you recommend",
    r"would you recommend",
    r"\bis\b[^?]{0,40}\btrusted\b",
    r"\bis\b[^?]{0,40}\bsafe\b",
    r"\bis\b[^?]{0,40}\blegit\b",
    r"\bis\b[^?]{0,40}\bscam\b",
    r"should i (use|avoid|buy|trust)",
    r"top alternatives",
    r"alternatives to",
    r"\bcompare\b",
    r"compete[sd]? with",
    r"\bbetter than\b",
    r"\bworth it\b",
    r"\bgood option\b",
    r"\breviews?\b",
    r"\bcomplaints?\b",
)

# Positioning vocabulary that pulls models into spam/penalty framing even when the
# question itself is polite. Identified empirically from Prompt Safety Test v1, where
# Gemini attached penalty warnings to the tier-2/tier-3 and high-volume questions.
RISKY_POSITIONING: tuple[str, ...] = (
    r"\bbulk\b",
    r"\bhigh[- ]volume\b",
    r"\bmass[- ](tier|link|produc)",
    r"\btier\s*[23]\b",
    r"\blow[- ]quality\b",
    r"\bcheap\b",
    r"\bspam\w*",
    r"\b(thousands|millions|hundreds of thousands) of (links|backlinks)\b",
    r"\bautomated links?\b",
    r"\blink farms?\b",
)


def lint_questions(questions: list[Question]) -> list[tuple[int, str, str]]:
    """Return (question_id, matched_phrase, text) for every risky prompt found.

    Covers both judgment phrasing (invites a verdict) and risky positioning
    vocabulary (invites spam/penalty framing).
    """
    hits: list[tuple[int, str, str]] = []
    for q in questions:
        low = q.text.lower()
        for pat in (*RISKY_PHRASES, *RISKY_POSITIONING):
            m = re.search(pat, low)
            if m:
                hits.append((q.id, m.group(0), q.text))
                break
    return hits

# Niche clauses guarantee STEP 2's "context around the niche" on every question.
# Having 3 variants also makes the (template x keyword x niche) pool large enough
# (>= 3*9*3 = 81) that even ELITE's 50 questions are all unique for any valid
# keyword count (3-7).
NICHE_CLAUSES: tuple[str, str, str] = (
    "(in the {niche} space)",
    "- focused on {niche}",
    "for {niche} clients",
)


def _squash_repeats(text: str) -> str:
    """Collapse an adjacent duplicated word, allowing a singular/plural pair.

    A keyword can already end in a word the template adds (e.g. keyword
    "...backlink campaigns" + template "... campaign planning"), which reads badly
    in a prompt sent to a real model.
    """
    words = text.split()
    out: list[str] = []
    for w in words:
        if out:
            a, b = out[-1].lower().strip(".,?"), w.lower().strip(".,?")
            if a == b or a == b + "s" or b == a + "s":
                continue
        out.append(w)
    return " ".join(out)


def _render_template(tpl: _Template, brand: str, keyword: str, niche_clause: str, niche: str) -> str:
    base = _squash_repeats(tpl.text.format(brand=brand, keyword=keyword))
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


def resolve_mode(ci: ClientInput, mode: str | None = None) -> str:
    """Pick the query mode: explicit argument > client input > default."""
    chosen = (mode or getattr(ci, "query_mode", "") or DEFAULT_QUERY_MODE).lower()
    if chosen not in QUERY_MODES:
        raise ValueError(
            f"Unknown query_mode '{chosen}'. Choose one of: {', '.join(sorted(QUERY_MODES))}."
        )
    return chosen


def generate_questions(ci: ClientInput, n: int, mode: str | None = None) -> list[Question]:
    """Generate exactly ``n`` unique questions for the client in the chosen mode."""
    chosen = resolve_mode(ci, mode)
    templates = QUERY_MODES[chosen]
    use_alias = chosen in ALIAS_MODES
    keywords = ci.keywords
    questions: list[Question] = []
    for (t, k, c) in _candidate_order(len(templates), len(keywords), len(NICHE_CLAUSES)):
        if len(questions) >= n:
            break
        tpl = templates[t]
        kw = keywords[k]
        asked = safe_keyword(kw) if use_alias else kw
        text = _render_template(tpl, ci.brand, asked, NICHE_CLAUSES[c], ci.niche)
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
    lines.append("  1. Take a FULL-PAGE screenshot of the whole answer (not cropped) and save it as")
    lines.append("     `screenshots/q{ID}_{model}.png` (lower-case model). It must show the prompt,")
    lines.append("     the complete answer, and visible model/interface context. See")
    lines.append("     `screenshots/EXPECTED_FILES.txt` and docs/SCREENSHOT_GUIDE.md for the rules + fallback.")
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
