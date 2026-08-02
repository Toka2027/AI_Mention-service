"""Tests for query modes (benefit vs audit) and the sentiment/risk screen.

The risk screen exists to stop a brand-damaging answer reaching a client report, so
both failure directions matter and are tested: it must catch real steer-away
language, and it must NOT flag ordinary SEO vocabulary used in generic advice.
"""

from __future__ import annotations

from engine import generator, sentiment
from engine.models import ClientInput


def _ci(**kw) -> ClientInput:
    base = dict(
        brand="1BillionLinks",
        website="https://1billionlinks.com",
        keywords=["SEO link building", "backlinks", "press release distribution"],
        niche="SEO link building and backlink services",
        package="PRO",
    )
    base.update(kw)
    return ClientInput(**base)


# --- query modes -------------------------------------------------------------

def test_benefit_is_the_default_mode():
    assert generator.resolve_mode(_ci()) == "benefit"


def test_explicit_mode_beats_input_which_beats_default():
    assert generator.resolve_mode(_ci(query_mode="audit")) == "audit"
    assert generator.resolve_mode(_ci(query_mode="audit"), "benefit") == "benefit"


def test_unknown_mode_is_rejected():
    try:
        generator.resolve_mode(_ci(), "nonsense")
    except ValueError as exc:
        assert "nonsense" in str(exc)
    else:
        raise AssertionError("an unknown query mode must be rejected")


def test_benefit_questions_are_clean_and_audit_questions_are_not():
    ci = _ci()
    benefit = generator.generate_questions(ci, 25, mode="benefit")
    audit = generator.generate_questions(ci, 25, mode="audit")
    assert generator.lint_questions(benefit) == [], "benefit mode must emit no risky prompts"
    assert generator.lint_questions(audit), "audit mode is expected to contain risky prompts"


def test_benefit_questions_keep_brand_keyword_and_niche():
    ci = _ci()
    for q in generator.generate_questions(ci, 25):
        assert ci.brand in q.text
        assert q.keyword in q.text
        assert ci.niche in q.text


def test_benefit_questions_are_unique_and_well_formed():
    ci = _ci()
    qs = generator.generate_questions(ci, 25)
    assert len({q.text for q in qs}) == len(qs)
    for q in qs:  # no doubled words from keyword/template collisions
        words = [w.lower().strip(".,?") for w in q.text.split()]
        assert not any(a == b for a, b in zip(words, words[1:])), q.text


# --- risk screen: must catch real damage -------------------------------------

def test_steer_away_language_is_unsafe():
    answer = ("If you're asking whether I'd recommend 1BillionLinks for a website you "
              "care about, my answer is no. I would avoid it. The business model is a "
              "red flag and the value for serious SEO is 2/10.")
    v = sentiment.review_answer(answer, "1BillionLinks")
    assert v["sentiment"] == sentiment.UNSAFE
    assert v["safe"] is False


def test_risk_language_tied_to_the_brand_is_unsafe():
    answer = ("Pointing thousands of low-cost links at a client's money site can trigger "
              "algorithmic or manual spam penalties. To safely utilize high-volume "
              "services like 1BillionLinks, keep them on Tier 2.")
    v = sentiment.review_answer(answer, "1BillionLinks")
    assert v["sentiment"] == sentiment.UNSAFE


# --- risk screen: must NOT flag generic advice -------------------------------

def test_generic_seo_vocabulary_is_not_flagged():
    """'Avoiding spammy links' describes good practice - it is not an accusation."""
    answer = ("1BillionLinks provides SEO link building services. A good campaign helps by "
              "identifying authoritative websites, securing editorial placements, and "
              "avoiding low-quality or spammy link sources. This supports long-term growth.")
    v = sentiment.review_answer(answer, "1BillionLinks")
    assert v["safe"] is True
    assert v["sentiment"] != sentiment.UNSAFE
    assert "spammy" in " ".join(v["generic_hazards"])


def test_audit_capability_wording_is_not_flagged():
    """'Toxic links that may need attention' describes what the service reviews."""
    answer = ("A service like 1BillionLinks would first evaluate factors such as domain "
              "authority, referring domains, and toxic/spammy links that may need "
              "attention. This helps establish a baseline and supports planning.")
    v = sentiment.review_answer(answer, "1BillionLinks")
    assert v["safe"] is True
    assert v["sentiment"] != sentiment.UNSAFE


def test_unknown_brand_is_a_visibility_gap_not_a_risk():
    answer = ("I don't have specific information about 1BillionLinks. It may be a smaller "
              "or newer provider in this space.")
    v = sentiment.review_answer(answer, "1BillionLinks")
    assert v["sentiment"] == sentiment.NEUTRAL
    assert v["safe"] is True
    assert v["brand_known"] is False


def test_positive_service_description_is_positive():
    answer = ("1BillionLinks provides bulk link building that helps agencies scale. It "
              "offers press release distribution, supports tiered campaigns, and enables "
              "teams to benefit from high-volume delivery. Useful for resellers.")
    v = sentiment.review_answer(answer, "1BillionLinks")
    assert v["sentiment"] == sentiment.POSITIVE
    assert v["safe"] is True


def test_empty_answer_is_not_safe():
    v = sentiment.review_answer("", "1BillionLinks")
    assert v["safe"] is False


# --- review table ------------------------------------------------------------

def test_summarize_counts_and_flags_per_model():
    rows = [
        {"question_id": 1, "query": "q", "model": "chatgpt", "sentiment": sentiment.POSITIVE,
         "safe": "Yes", "issue": "", "screenshot": "a.png"},
        {"question_id": 2, "query": "q", "model": "chatgpt", "sentiment": sentiment.UNSAFE,
         "safe": "No", "issue": "bad", "screenshot": "b.png"},
    ]
    s = sentiment.summarize(rows)["chatgpt"]
    assert s["total"] == 2 and s["unsafe_ids"] == [2]
    assert "Q2" in sentiment.format_table(rows)


# --- regression: consequence framing must not slip through --------------------

def test_consequence_framing_is_unsafe_even_when_worded_helpfully():
    """The hardest case: calm advisory prose saying harm follows from the service.

    An earlier version of the screen passed these because words like "safely" and
    "avoid" sat near the hazard word. The hazard here is the OUTCOME, not the thing
    being avoided, so no nearby cue may excuse it.
    """
    cases = [
        "Flat, uncalculated bulk link-building can trigger algorithmic or manual "
        "penalties. To safely leverage a high-volume service, it must be isolated to "
        "lower, non-risky tiers.",
        "While bulk link services can rapidly expand a backlink profile, improper "
        "integration can risk search engine penalties.",
        "This enhances authority flowing to your core targets without exposing your "
        "main site to direct algorithmic penalties.",
        "Never point low-quality mass-tier services directly to your main domain. "
        "Keep them strictly isolated to Tiers 2 and 3 to act as a buffer.",
    ]
    for text in cases:
        v = sentiment.review_answer(text, "1BillionLinks")
        assert v["sentiment"] == sentiment.UNSAFE, f"missed consequence framing: {text[:60]}"
        assert v["safe"] is False


def test_service_helping_avoid_penalties_is_still_safe():
    """The mirror image: the service PREVENTS the harm. Must not be flagged."""
    answer = ("By focusing on safe, sustainable link acquisition, 1BillionLinks helps "
              "workflows avoid algorithmic penalties associated with manipulative or "
              "automated link schemes. It supports and benefits structured campaigns.")
    v = sentiment.review_answer(answer, "1BillionLinks")
    assert v["safe"] is True
    assert v["sentiment"] != sentiment.UNSAFE


def test_quality_filter_vocabulary_is_still_safe():
    """'Spam indicators', 'spam checks', 'Avoid: spam networks' are QA vocabulary."""
    for answer in [
        "Quality filters: Domain relevance, Organic traffic, Editorial standards, "
        "Spam indicators. 1BillionLinks provides and supports this analysis.",
        "Monitoring: Backlink audits, ranking tracking, spam checks. This helps "
        "1BillionLinks protect the link profile and offers useful reporting.",
        "Prefer editorial links. Avoid: Spam networks, Automated link farms. "
        "1BillionLinks supports and enables this filtering, which benefits teams.",
    ]:
        v = sentiment.review_answer(answer, "1BillionLinks")
        assert v["safe"] is True, f"false positive on QA vocabulary: {answer[:60]}"


def test_link_hygiene_vocabulary_is_safe():
    """'Removal of toxic placements' is the service cleaning up, not wrongdoing."""
    answer = ("A modern SEO plan covers sustainable link velocity, natural anchor text "
              "distribution, and removal of toxic or low-quality placements. "
              "1BillionLinks provides and supports this, which benefits agencies.")
    v = sentiment.review_answer(answer, "1BillionLinks")
    assert v["safe"] is True, v["issue"]
    assert v["sentiment"] != sentiment.UNSAFE
