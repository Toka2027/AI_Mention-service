"""Build the sanitized, sales-safe SAMPLE report from the 1BillionLinks pilot.

Outputs (run from service_engine/):
    docs/samples/1billionlinks_sample_report.md
    docs/samples/1billionlinks_sample_report.pdf

The content is curated for sales/demo: weak AI recognition is framed as a visibility
gap / opportunity, never as damage. No guarantees, no banned wording. Reproducible:
    python tools/build_sample_report.py
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

OUT_DIR = Path("docs/samples")
STEM = "1billionlinks_sample_report"

_REPL = {"–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "…": "...", "•": "*"}


def _latin1(t: str) -> str:
    for a, b in _REPL.items():
        t = t.replace(a, b)
    return t.encode("latin-1", "replace").decode("latin-1")


# --- Curated, sales-safe content (illustrative SAMPLE) ----------------------
# (heading, kind, lines)  kind in {"p","bullet"}
TITLE = "AI Visibility Baseline - Sample Report"
SUBTITLE = "Illustrative sample - 1BillionLinks - PRO package - 2026-06-28"
BANNER = (
    "SAMPLE / ILLUSTRATIVE. Prepared from a pilot run to show the deliverable format. "
    "Findings are a point-in-time baseline of how AI assistants currently answer brand "
    "questions; they are not a promise of future results."
)

SECTIONS = [
    ("1. What this report covers", "p", [
        "AI Mention tests how today's AI assistants (ChatGPT, Gemini, Claude, Perplexity) currently "
        "answer real questions about your brand and keywords, captures those answers as evidence, "
        "reviews which brands and sources the AI associates with your niche, and turns the findings "
        "into crawlable support pages you can publish.",
        "It is an AI visibility baseline and brand/entity association review - a measurable starting "
        "point you can re-test over time.",
    ]),
    ("2. Snapshot", "bullet", [
        "Brand: 1BillionLinks (SEO link building & backlink services)",
        "Questions tested: 25 brand + keyword questions",
        "AI tools tested: ChatGPT, Gemini, Claude, Perplexity",
        "Crawlable support pages produced: 12 (with FAQ + WebPage schema)",
        "Evidence: full-page answer screenshots + a master data table",
    ]),
    ("3. AI visibility baseline (the opportunity)", "p", [
        "Across the questions tested, the AI assistants did not yet consistently recognise "
        "1BillionLinks as a go-to brand for these keywords. This is a normal early-stage baseline for "
        "a brand that has not yet built strong topical associations in AI answers - and it is exactly "
        "the opportunity this service is designed to map.",
        "In other words: there is open space to become one of the brands AI assistants reference for "
        "these topics, starting from a clear, measured baseline.",
    ]),
    ("4. Competitor association insight", "p", [
        "When asked about this niche, the AI assistants most often surfaced these brands. They show "
        "the associations currently occupying the space - useful targets to benchmark against:",
    ]),
    ("", "bullet", [
        "Link-building providers: FATJOE, Loganix, The HOTH, Authority Builders, Stan Ventures",
        "Press-release distribution: EIN Presswire, Newswire, PRWeb, Brandpush",
        "Authority measurement tools: Moz, Ahrefs, Semrush",
    ]),
    ("5. Keywords tested", "bullet", [
        "SEO link building",
        "backlinks",
        "press release distribution",
        "domain authority",
        "tier 2 and tier 3 backlink campaigns",
    ]),
    ("6. Opportunity areas & recommended next steps", "bullet", [
        "Publish the crawlable support pages so there is clear, on-topic content linking the brand to "
        "each target keyword.",
        "Prioritise the keywords where competitors are most strongly associated - these are the "
        "highest-value gaps to close.",
        "Re-test the same questions on a regular cycle to track how AI recognition of the brand "
        "changes over time.",
        "Strengthen brand/entity signals (consistent name, descriptions, and references) across the "
        "brand's own web presence.",
    ]),
    ("7. What the full delivery includes", "bullet", [
        "Question set + full-page answer screenshots from each AI tool tested",
        "Master data table (questions, answers, sources, competitors, brand appearances)",
        "Crawlable support pages with schema + a sitemap",
        "This baseline report + an order brief, packaged as a delivery ZIP",
    ]),
    ("8. Scope & disclaimer", "p", [
        "This is an observational baseline. It documents how AI tools currently answer brand "
        "questions at a point in time. It does not inject, train, manipulate, or influence AI models, "
        "and it does not promise or guarantee AI mentions, LLM visibility, search rankings, or "
        "indexing. Publishing support pages helps discovery and crawling only.",
    ]),
]


def write_markdown(path: Path) -> None:
    out = [f"# {TITLE}", "", f"*{SUBTITLE}*", "", f"> {BANNER}", ""]
    for heading, kind, lines in SECTIONS:
        if heading:
            out += ["", f"## {heading}", ""]
        if kind == "bullet":
            out += [f"- {ln}" for ln in lines]
        else:
            out += [ln + "\n" for ln in lines]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def write_pdf(path: Path) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    def mc(text, h, style="", size=11, wrap="WORD"):
        pdf.set_font("Helvetica", style, size)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, h, _latin1(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT, wrapmode=wrap)

    mc(TITLE, 9, "B", 18)
    mc(SUBTITLE, 6, "I", 11)
    pdf.ln(1)
    mc(BANNER, 6, "", 10)
    pdf.ln(2)
    for heading, kind, lines in SECTIONS:
        if heading:
            pdf.ln(2)
            mc(heading, 7, "B", 13)
        for ln in lines:
            if kind == "bullet":
                mc("- " + ln, 6, "", 11, wrap="CHAR")
            else:
                mc(ln, 6, "", 11)
    pdf.output(str(path))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_markdown(OUT_DIR / f"{STEM}.md")
    write_pdf(OUT_DIR / f"{STEM}.pdf")
    print(f"Wrote {OUT_DIR / (STEM + '.md')} and {OUT_DIR / (STEM + '.pdf')}")


if __name__ == "__main__":
    main()
