"""Sentiment / risk screening for captured LLM answers.

Runs BEFORE anything reaches a client report, so a brand-damaging answer is caught
while it is still an internal finding. Deterministic and offline (no model call), in
keeping with the rest of the engine: the same answer always yields the same verdict.

This is a SCREEN, not a verdict. It deliberately over-flags - an answer marked
"Unsafe" must be read by the operator, who makes the final call. It never edits,
hides, or rewrites an answer; it only labels what was really captured.

Classes:
    Positive                 answer explains the service in useful, favourable terms
    Neutral                  factual/mixed, or the model does not know the brand
    Negative                 cautionary framing, doubts, quality concerns
    Unsafe for client report brand-damaging: recommends against, alleges bad practice
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

POSITIVE, NEUTRAL, NEGATIVE, UNSAFE = (
    "Positive", "Neutral", "Negative", "Unsafe for client report",
)

# VERDICTS: the model is steering the reader away. Always unsafe - there is no
# educational reading of "I would avoid this service".
VERDICT_MARKERS: tuple[str, ...] = (
    r"\bi would avoid\b", r"\bwould avoid\b",
    r"\bdo not use\b", r"\bdon't use\b", r"\bwouldn't use\b", r"\bwould not use\b",
    r"\bnot recommend", r"\bwouldn't recommend\b", r"\bwould not recommend\b",
    r"\bsteer clear\b", r"\bstay away\b", r"\bwaste of money\b",
    r"\bscam\b", r"\bfraud", r"\bred flag", r"\bnot worth\b",
)

# CONSEQUENCES: the answer says harm FOLLOWS FROM using this kind of service. This is
# the most damaging pattern and the easiest to miss, because it is written in calm,
# advisory prose ("can trigger penalties", "must be isolated", "never point ... at").
# No avoidance cue can excuse these - the hazard is the OUTCOME, not the thing avoided.
CONSEQUENCE_MARKERS: tuple[str, ...] = (
    r"\b(can|could|may|might|will)\s+(trigger|cause|result in|lead to|invite)\b[^.]{0,60}"
    r"\b(penalt|deindex|de-index|ban\b|sanction|manual action)",
    r"\brisk\w*\b[^.]{0,40}\b(penalt|deindex|de-index|manual action)",
    r"\bexpos\w+\b[^.]{0,60}\b(penalt|deindex|de-index|manual action)",
    r"\b(penalt|deindex|de-index)\w*\b[^.]{0,40}\bif you\b",
    r"\bnever point\b",
    r"\bmust be isolated\b",
    r"\bkeep (them|it) (strictly )?isolated\b",
    r"\bact as a buffer\b",
    r"\bnon[- ]risky tiers?\b",
    r"\bbuffer(ing)? the main domain\b",
    r"\bwithout exposing\b[^.]{0,40}\b(site|domain)",
)

# HAZARDS: SEO risk vocabulary. Genuinely damaging when asserted ABOUT the brand,
# but completely normal in generic best-practice prose ("avoiding spammy links",
# "toxic links that may need attention"). Context decides - see `_hazard_verdict`.
HAZARD_MARKERS: tuple[str, ...] = (
    r"\bblack[- ]?hat\b", r"\bpenalt(y|ies|ise|ize|ised|ized)", r"\bmanual action\b",
    r"\bdeindex\w*", r"\bde-index\w*", r"\btoxic\b", r"\blink spam\b",
    r"\bspammy\b", r"\bspam signals?\b", r"\bbanned\b",
)

# A hazard word near one of these is describing what to AVOID, or what a service
# screens out / audits for - the opposite of an accusation. Checked on BOTH sides:
# "avoiding spammy links" and "toxic links that may need attention" are both benign.
AVOIDANCE_CUES: tuple[str, ...] = (
    "avoid", "avoiding", "prevent", "preventing", "without", "instead of",
    "rather than", "free of", "reduce", "reducing", "minimi", "identify",
    "identifying", "screen out", "filter", "need attention", "may need",
    "watch for", "look for", "audit", "disavow", "clean up", "steer away from",
    "protect against", "guard against", "no ", "not ", "never ",
    # the service examines/assesses these - describes capability, not wrongdoing
    "evaluate", "evaluating", "assess", "assessing", "review", "reviewing",
    "analyz", "analys", "check", "checking", "flag", "detect",
    # the service cleans these up - link hygiene, not an accusation
    "remov", "clean", "prun", "strip", "weed out", "eliminat", "no more",
)

# Cautionary framing: not an accusation, but not safe to publish unreviewed.
NEGATIVE_MARKERS: tuple[str, ...] = (
    r"\bcaution\b", r"\bcareful\b", r"\brisk", r"\bconcern", r"\bquestionable\b",
    r"\blow[- ]quality\b", r"\bpoor\b", r"\bmixed review", r"\bcomplaint",
    r"\bbeware\b", r"\bdisappear", r"\bunverified\b", r"\bcannot verify\b",
    r"\bcan't verify\b", r"\bno independent\b", r"\bbe skeptical\b", r"\bdubious\b",
    r"\bautomated links?\b", r"\blow[- ]value\b", r"\bdiminishing\b",
)

# Service-comprehension language: the model is explaining what the brand offers.
POSITIVE_MARKERS: tuple[str, ...] = (
    r"\bhelps?\b", r"\bbenefit", r"\buseful\b", r"\bsupports?\b", r"\beffective\b",
    r"\badvantage", r"\bvaluable\b", r"\bstrength", r"\bwell[- ]suited\b",
    r"\bideal for\b", r"\bdesigned to\b", r"\bprovides?\b", r"\boffers?\b",
    r"\benables?\b", r"\bstreamlines?\b", r"\bsuited to\b", r"\buse cases?\b",
)

# The model does not know the brand - a visibility gap, not a reputation problem.
UNKNOWN_MARKERS: tuple[str, ...] = (
    r"\bi (don't|do not) have\b[^.]{0,60}\b(information|data|details|knowledge)\b",
    r"\bnot familiar with\b", r"\bno (specific|reliable|verified) information\b",
    r"\bi'm not aware of\b", r"\bi am not aware of\b",
    r"\bcouldn't find\b", r"\bcould not find\b", r"\bno public",
)


def _hits(patterns: tuple[str, ...], text: str) -> list[str]:
    found: list[str] = []
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            found.append(m.group(0).strip())
    return found


def _hazard_verdict(text: str, brand: str) -> tuple[list[str], list[str]]:
    """Split hazard-word occurrences into (asserted_about_brand, generic_advice).

    A hazard word is treated as generic SEO advice when an avoidance cue sits just
    before it ("avoiding spammy links"), and as an assertion about the brand when the
    brand name appears close by without such a cue.
    """
    asserted: list[str] = []
    generic: list[str] = []
    b = (brand or "").lower()
    for pat in HAZARD_MARKERS:
        for m in re.finditer(pat, text):
            # Narrow windows: the cue must apply to THIS hazard word ("avoid: spam
            # networks", "spam checks"), not merely appear somewhere in the paragraph.
            # A wide window is what let "can trigger ... penalties" pass as benign.
            lead = text[max(0, m.start() - 28):m.start()]
            trail = text[m.end():m.end() + 28]
            if any(cue in lead for cue in AVOIDANCE_CUES) or \
               any(cue in trail for cue in AVOIDANCE_CUES):
                generic.append(m.group(0).strip())
                continue
            window = text[max(0, m.start() - 220):m.start() + 220]
            (asserted if b and b in window else generic).append(m.group(0).strip())
    return asserted, generic


def review_answer(answer: str, brand: str = "") -> dict:
    """Classify one captured answer. Returns sentiment, safety and the evidence."""
    text = (answer or "").lower()
    if not text.strip():
        return {"sentiment": NEUTRAL, "safe": False, "issue": "empty answer",
                "unsafe_hits": [], "negative_hits": [], "positive_hits": [],
                "brand_known": False, "brand_mentioned": False}

    verdicts = _hits(VERDICT_MARKERS, text)
    consequences = _hits(CONSEQUENCE_MARKERS, text)
    hazards_about_brand, hazards_generic = _hazard_verdict(text, brand)
    negative = _hits(NEGATIVE_MARKERS, text)
    positive = _hits(POSITIVE_MARKERS, text)
    unknown = _hits(UNKNOWN_MARKERS, text)
    brand_mentioned = bool(brand) and brand.lower() in text
    unsafe = verdicts + consequences + hazards_about_brand

    if verdicts:
        sentiment, safe = UNSAFE, False
        issue = f"steers the reader away: {', '.join(sorted(set(verdicts))[:4])}"
    elif consequences:
        sentiment, safe = UNSAFE, False
        issue = (f"says harm follows from using this kind of service: "
                 f"{'; '.join(sorted(set(c[:60] for c in consequences))[:3])}")
    elif hazards_about_brand:
        sentiment, safe = UNSAFE, False
        issue = (f"risk language tied to the brand: "
                 f"{', '.join(sorted(set(hazards_about_brand))[:4])}")
    elif len(negative) >= 3 and len(negative) > len(positive):
        sentiment, safe = NEGATIVE, False
        issue = f"cautionary framing: {', '.join(sorted(set(negative))[:4])}"
    elif unknown and len(positive) < 3:
        sentiment, safe = NEUTRAL, True
        issue = "model does not appear to know the brand (visibility gap)"
    elif len(positive) >= 3 and len(negative) <= 1:
        sentiment, safe = POSITIVE, True
        issue = ""
    elif negative:
        sentiment, safe = NEUTRAL, True
        issue = f"minor cautionary wording: {', '.join(sorted(set(negative))[:3])}"
    else:
        sentiment, safe = NEUTRAL, True
        issue = ""

    return {
        "sentiment": sentiment, "safe": safe, "issue": issue,
        "unsafe_hits": sorted(set(unsafe)), "negative_hits": sorted(set(negative)),
        "positive_hits": sorted(set(positive)),
        "generic_hazards": sorted(set(hazards_generic)),
        "brand_known": not unknown, "brand_mentioned": brand_mentioned,
    }


def review_order(
    captures_dir: str | Path,
    shots_dir: str | Path,
    models: list[str],
    questions: list,
    brand: str = "",
) -> list[dict]:
    """Screen every captured answer for an order. Only real captures are included."""
    caps, shots = Path(captures_dir), Path(shots_dir)
    rows: list[dict] = []
    for model in models:
        m = model.lower()
        mdir = caps / m
        if not mdir.exists():
            continue
        for q in questions:
            afile = mdir / f"q{q.id}.txt"
            if not afile.exists():
                continue
            answer = afile.read_text(encoding="utf-8").strip()
            verdict = review_answer(answer, brand)
            shot = shots / f"q{q.id}_{m}.png"
            evidence = (mdir / f"q{q.id}.evidence.txt")
            rows.append({
                "question_id": q.id, "query": q.text, "model": model,
                "sentiment": verdict["sentiment"],
                "safe": "Yes" if verdict["safe"] else "No",
                "issue": verdict["issue"],
                "answer_path": str(afile),
                "screenshot": str(shot) if shot.exists() else "MISSING",
                "evidence_type": evidence.read_text(encoding="utf-8").strip()
                                 if evidence.exists() else "none",
                "answer_chars": len(answer),
                "brand_known": verdict["brand_known"],
            })
    return rows


def write_review_csv(rows: list[dict], path: str | Path) -> None:
    cols = ["question_id", "query", "model", "sentiment", "safe", "issue",
            "evidence_type", "answer_chars", "brand_known", "answer_path", "screenshot"]
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def format_table(rows: list[dict]) -> str:
    """Markdown risk-review table (the format requested for sign-off)."""
    if not rows:
        return "No captured answers to review."
    out = ["| Query ID | Query | Model | Sentiment | Safe to use? | Issue if unsafe | "
           "Answer path | Screenshot path |",
           "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        q = r["query"] if len(r["query"]) <= 70 else r["query"][:67] + "..."
        shot = Path(r["screenshot"]).name if r["screenshot"] != "MISSING" else "**MISSING**"
        ans = Path(r.get("answer_path", "")).name or "-"
        out.append(f"| Q{r['question_id']} | {q} | {r['model']} | {r['sentiment']} | "
                   f"{r['safe']} | {r['issue'] or '-'} | {ans} | {shot} |")
    n_unsafe = sum(1 for r in rows if r["safe"] == "No")
    out.append("")
    out.append(f"**{len(rows)} answers reviewed - {n_unsafe} flagged as not safe to use.**")
    return "\n".join(out)


def summarize(rows: list[dict]) -> dict:
    """Per-model counts, for the scale/no-scale recommendation."""
    summary: dict = {}
    for r in rows:
        s = summary.setdefault(r["model"], {POSITIVE: 0, NEUTRAL: 0, NEGATIVE: 0, UNSAFE: 0,
                                           "total": 0, "unsafe_ids": []})
        s[r["sentiment"]] += 1
        s["total"] += 1
        if r["safe"] == "No":
            s["unsafe_ids"].append(r["question_id"])
    return summary
