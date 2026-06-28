"""Data models, package definitions, and input validation.

Maps to STEP 1 of the service document (Collect Inputs) and the Packages &
Pricing section. Validation lives here so callers always work with a checked
``ClientInput``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


# --- Packages (from the document's "Packages & Pricing" section) -------------
# Each tier fixes: how many questions are generated (STEP 2), which LLMs are in
# scope (STEP 3), how many crawlable support pages are built (STEP 5), and whether
# schema markup is emitted (introduced at PRO in the document).

@dataclass(frozen=True)
class Package:
    name: str
    price_usd: int
    n_questions: int
    models: tuple[str, ...]
    n_pages: int
    schema: bool


PACKAGES: dict[str, Package] = {
    "BASIC": Package(
        name="BASIC",
        price_usd=29,
        n_questions=10,
        models=("ChatGPT", "Gemini"),
        n_pages=5,
        schema=False,
    ),
    "PRO": Package(
        name="PRO",
        price_usd=59,
        n_questions=25,
        models=("ChatGPT", "Gemini", "Claude", "Perplexity"),
        n_pages=12,
        schema=True,
    ),
    "ELITE": Package(
        name="ELITE",
        price_usd=99,
        n_questions=50,
        models=("ChatGPT", "Gemini", "Claude", "Perplexity", "Llama"),
        n_pages=25,
        schema=True,
    ),
}


# --- Client input (STEP 1) ---------------------------------------------------

# Recommended intake fields (beyond the hard-required core). Missing ones do not
# block a run; they lower the "intake completeness" score and raise a warning so
# the operator knows what to chase before delivery. See docs/CLIENT_REQUIREMENTS.md.
RECOMMENDED_INTAKE = (
    "country",
    "language",
    "brand_variations",
    "competitors_known",
    "target_urls",
    "preferred_positioning",
    "services_to_highlight",
    "topics_to_avoid",
    "compliance_notes",
    "delivery_contact",
)


def _as_str(value) -> str:
    return str(value).strip() if value is not None else ""


def _as_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(v).strip() for v in value if str(v).strip()]


@dataclass
class ClientInput:
    # --- hard-required core (STEP 1) ---
    brand: str
    website: str
    keywords: list[str]
    niche: str
    package: str
    # --- operational identifiers ---
    order_id: str = ""
    client_slug: str = ""
    # --- recommended intake (warn if missing) ---
    brand_variations: list[str] = field(default_factory=list)
    country: str = ""
    language: str = ""
    competitors_known: list[str] = field(default_factory=list)
    target_urls: list[str] = field(default_factory=list)
    preferred_positioning: str = ""
    services_to_highlight: list[str] = field(default_factory=list)
    topics_to_avoid: list[str] = field(default_factory=list)
    compliance_notes: str = ""
    delivery_contact: str = ""
    # --- optional extras ---
    brand_descriptions: str = ""
    preferred_models: list[str] = field(default_factory=list)
    question_angles: list[str] = field(default_factory=list)
    example_customers: list[str] = field(default_factory=list)
    negative_competitors: list[str] = field(default_factory=list)
    tone_notes: str = ""
    # --- runtime ---
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: str | Path) -> "ClientInput":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Input file not found: {p}")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Input file is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("Input JSON must be an object.")

        ci = cls(
            brand=_as_str(data.get("brand")),
            website=_as_str(data.get("website")),
            keywords=_as_list(data.get("keywords")),
            niche=_as_str(data.get("niche")),
            package=_as_str(data.get("package")).upper(),
            order_id=_as_str(data.get("order_id")),
            client_slug=_as_str(data.get("client_slug")),
            brand_variations=_as_list(data.get("brand_variations")),
            country=_as_str(data.get("country")),
            language=_as_str(data.get("language")),
            competitors_known=_as_list(data.get("competitors_known")),
            target_urls=_as_list(data.get("target_urls")),
            preferred_positioning=_as_str(data.get("preferred_positioning")),
            services_to_highlight=_as_list(data.get("services_to_highlight")),
            topics_to_avoid=_as_list(data.get("topics_to_avoid")),
            compliance_notes=_as_str(data.get("compliance_notes")),
            delivery_contact=_as_str(data.get("delivery_contact")),
            brand_descriptions=_as_str(data.get("brand_descriptions")),
            preferred_models=_as_list(data.get("preferred_models")),
            question_angles=_as_list(data.get("question_angles")),
            example_customers=_as_list(data.get("example_customers")),
            negative_competitors=_as_list(data.get("negative_competitors")),
            tone_notes=_as_str(data.get("tone_notes")),
        )
        ci.validate()
        return ci

    @property
    def pkg(self) -> Package:
        return PACKAGES[self.package]

    def all_brand_terms(self) -> list[str]:
        """Brand plus its variations, de-duplicated, brand first."""
        terms: list[str] = [self.brand]
        for v in self.brand_variations:
            if v and v not in terms:
                terms.append(v)
        return terms

    def intake_completeness(self) -> tuple[int, int, list[str]]:
        """Return (filled, total, missing[]) over the recommended intake fields."""
        missing: list[str] = []
        for fname in RECOMMENDED_INTAKE:
            val = getattr(self, fname)
            if not val:
                missing.append(fname)
        total = len(RECOMMENDED_INTAKE)
        return total - len(missing), total, missing

    def validate(self) -> None:
        """Raise ValueError on any blocking problem; collect soft warnings."""
        if not self.brand:
            raise ValueError("Missing required field: 'brand'.")
        if not self.niche:
            raise ValueError("Missing required field: 'niche'.")
        if not self.website:
            raise ValueError("Missing required field: 'website'.")
        if not (self.website.startswith("http://") or self.website.startswith("https://")):
            raise ValueError("'website' must start with http:// or https://")
        # The document specifies 3-7 target keywords (STEP 1).
        if not (3 <= len(self.keywords) <= 7):
            raise ValueError(
                f"'keywords' must contain 3 to 7 items (got {len(self.keywords)})."
            )
        if self.package not in PACKAGES:
            raise ValueError(
                f"Unknown package '{self.package}'. Choose one of: "
                f"{', '.join(PACKAGES)}."
            )
        # Soft warning: PRO/ELITE explicitly add brand variations (STEP 5).
        if self.pkg.schema and len(self.brand_variations) < 2:
            self.warnings.append(
                f"{self.package} package adds brand variations, but only "
                f"{len(self.brand_variations)} provided (2-4 recommended)."
            )
        # Soft warning: recommended intake completeness (does not block).
        filled, total, missing = self.intake_completeness()
        if missing:
            self.warnings.append(
                f"intake {filled}/{total} complete - missing recommended fields: "
                f"{', '.join(missing)} (see docs/CLIENT_REQUIREMENTS.md)."
            )


# --- Generated question (STEP 2) --------------------------------------------

@dataclass
class Question:
    id: int
    text: str
    template_id: str
    category: str
    keyword: str


# --- Captured LLM response (STEP 3 / STEP 4) --------------------------------

@dataclass
class ResponseRow:
    question_id: int
    model: str
    answer: str = ""
    urls: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    screenshot_filename: str = ""
    behavior_notes: str = ""

    PENDING = "[pending capture]"

    @property
    def is_captured(self) -> bool:
        a = (self.answer or "").strip()
        return bool(a) and a != self.PENDING
