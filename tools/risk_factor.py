"""Rule-based risk scoring for underwriting dimensions."""

from typing import Literal

from pydantic import BaseModel, Field


class RiskDimensionScore(BaseModel):
    dimension: str
    score: float = Field(..., ge=0.0, le=1.0)
    tier: Literal["low", "medium", "high"]
    notes: str


class RiskFactorInput(BaseModel):
    location: str
    has_pool: bool
    claims_history: int
    credit_score: int | None = None
    home_value: float
    age: int


class RiskFactorOutput(BaseModel):
    dimensions: list[RiskDimensionScore]
    composite_score: float = Field(..., ge=0.0, le=1.0)
    overall_tier: Literal["low", "medium", "high"]


# Rough hazard weights by state — not real actuarial data
_LOCATION_TIERS: dict[str, float] = {
    "california": 0.75,
    "florida": 0.85,
    "texas": 0.65,
    "new york": 0.70,
    "louisiana": 0.80,
}


def _tier_from_score(score: float) -> Literal["low", "medium", "high"]:
    if score < 0.35:
        return "low"
    if score < 0.65:
        return "medium"
    return "high"


class RiskFactorTool:
    """Scores individual risk dimensions and returns a structured breakdown."""

    name = "risk_factor_tool"
    description = (
        "Scores location, pool, claims, credit, home value, and age; "
        "returns a composite risk score."
    )

    @staticmethod
    def run(inp: RiskFactorInput) -> RiskFactorOutput:
        loc_key = inp.location.strip().lower()
        loc_score = _LOCATION_TIERS.get(loc_key, 0.55)
        dimensions: list[RiskDimensionScore] = [
            RiskDimensionScore(
                dimension="location_hazard",
                score=loc_score,
                tier=_tier_from_score(loc_score),
                notes=f"Hazard tier for {inp.location}",
            ),
            RiskDimensionScore(
                dimension="pool_liability",
                score=0.70 if inp.has_pool else 0.15,
                tier="high" if inp.has_pool else "low",
                notes="Pool increases liability exposure",
            ),
            RiskDimensionScore(
                dimension="claims_history",
                score=min(0.25 + inp.claims_history * 0.25, 1.0),
                tier=_tier_from_score(min(0.25 + inp.claims_history * 0.25, 1.0)),
                notes=f"{inp.claims_history} prior claim(s)",
            ),
        ]

        if inp.credit_score is not None:
            credit_norm = max(0, min(1, (850 - inp.credit_score) / 550))
            dimensions.append(
                RiskDimensionScore(
                    dimension="credit",
                    score=credit_norm,
                    tier=_tier_from_score(credit_norm),
                    notes=f"Credit score {inp.credit_score}",
                )
            )
        else:
            dimensions.append(
                RiskDimensionScore(
                    dimension="credit",
                    score=0.55,
                    tier="medium",
                    notes="Missing credit score — conservative default applied",
                )
            )

        value_score = min(inp.home_value / 2_000_000, 1.0) * 0.6 + 0.2
        dimensions.append(
            RiskDimensionScore(
                dimension="home_value",
                score=value_score,
                tier=_tier_from_score(value_score),
                notes=f"Insured value ${inp.home_value:,.0f}",
            )
        )

        age_score = 0.35 if inp.age >= 55 else (0.25 if inp.age < 30 else 0.20)
        dimensions.append(
            RiskDimensionScore(
                dimension="age",
                score=age_score,
                tier=_tier_from_score(age_score),
                notes=f"Policyholder age {inp.age}",
            )
        )

        composite = sum(d.score for d in dimensions) / len(dimensions)
        return RiskFactorOutput(
            dimensions=dimensions,
            composite_score=round(composite, 4),
            overall_tier=_tier_from_score(composite),
        )
