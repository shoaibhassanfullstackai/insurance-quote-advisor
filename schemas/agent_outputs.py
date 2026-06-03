from typing import Literal, Optional

from pydantic import BaseModel, Field


class RiskFactorItem(BaseModel):
    factor: str
    severity: Literal["low", "medium", "high"]
    rationale: str


class RiskAssessmentOutput(BaseModel):
    risk_factors: list[RiskFactorItem]
    overall_risk_level: Literal["low", "medium", "high"]
    reasoning: str
    tool_breakdown: Optional[dict] = None


class RecommendedCoverageItem(BaseModel):
    type: str
    limit: str
    rationale: str


class CoverageRecommendationOutput(BaseModel):
    recommended_coverages: list[RecommendedCoverageItem]
    reasoning: str


class PremiumRangeOutput(BaseModel):
    low: float
    high: float
    currency: str = "USD"


class PricingOutput(BaseModel):
    premium_range: PremiumRangeOutput
    reasoning: str
    heuristic_breakdown: Optional[dict] = None


class ValidatorOutput(BaseModel):
    consistent: bool
    issues: list[str] = Field(default_factory=list)
    adjustments: list[str] = Field(default_factory=list)
    reasoning: str


class RouterDecision(BaseModel):
    route: Literal["quote_pipeline", "follow_up", "reject"]
    reason: str
    follow_up_intent: Optional[str] = None
