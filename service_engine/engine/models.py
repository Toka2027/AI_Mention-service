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
# scope (STEP 3), how many indexing pages are built (STEP 5), and whether
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

@dataclass
class ClientInput:
    brand: str
    website: str
    keywords: list[str]
    niche: str
    package: str
    brand_variations: list[str] = field(default_factory=list)
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
            brand=str(data.get("brand", "")).strip(),
            website=str(data.get("website", "")).strip(),
            keywords=[str(k).strip() for k in data.get("keywords", []) if str(k).strip()],
            niche=str(data.get("niche", "")).strip(),
            package=str(data.get("package", "")).strip().upper(),
            brand_variations=[
                str(v).strip() for v in data.get("brand_variations", []) if str(v).strip()
            ],
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
