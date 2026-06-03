"""Premium estimate from home value and risk/coverage multipliers."""

from pydantic import BaseModel, Field


class PricingHeuristicInput(BaseModel):
    home_value: float
    composite_risk_score: float = Field(..., ge=0.0, le=1.0)
    has_pool: bool
    claims_history: int
    coverage_multiplier: float = Field(default=1.0, ge=0.5, le=2.5)
    location: str


class PricingHeuristicOutput(BaseModel):
    base_premium: float
    adjusted_premium: float
    low: float
    high: float
    currency: str = "USD"
    multipliers_applied: dict[str, float]


_LOCATION_MULT: dict[str, float] = {
    "california": 1.25,
    "florida": 1.35,
    "texas": 1.10,
    "new york": 1.20,
}


class PricingHeuristicTool:
    """Applies rule-based multipliers to a base premium."""

    name = "pricing_heuristic_tool"
    description = "Computes premium range from home value, risk score, and coverage multiplier."

    @staticmethod
    def run(inp: PricingHeuristicInput) -> PricingHeuristicOutput:
        # ~0.35% of insured value per year — see README assumptions
        base = inp.home_value * 0.0035
        loc_key = inp.location.strip().lower()
        loc_mult = _LOCATION_MULT.get(loc_key, 1.15)
        risk_mult = 0.85 + inp.composite_risk_score * 0.5
        pool_mult = 1.12 if inp.has_pool else 1.0
        claims_mult = 1.0 + inp.claims_history * 0.08
        cov_mult = inp.coverage_multiplier

        multipliers = {
            "location": loc_mult,
            "risk": round(risk_mult, 4),
            "pool": pool_mult,
            "claims": claims_mult,
            "coverage": cov_mult,
        }
        product = 1.0
        for v in multipliers.values():
            product *= v

        adjusted = base * product
        spread = 0.12 + inp.composite_risk_score * 0.08
        low = round(adjusted * (1 - spread), 2)
        high = round(adjusted * (1 + spread), 2)

        return PricingHeuristicOutput(
            base_premium=round(base, 2),
            adjusted_premium=round(adjusted, 2),
            low=low,
            high=high,
            multipliers_applied=multipliers,
        )
