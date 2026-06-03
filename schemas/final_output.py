from typing import Literal, Optional

from pydantic import BaseModel, Field


class RiskFactor(BaseModel):
    factor: str
    severity: Literal["low", "medium", "high"]
    rationale: str


class RecommendedCoverage(BaseModel):
    type: str
    limit: str
    rationale: str


class PremiumRange(BaseModel):
    low: float
    high: float
    currency: str = "USD"


class FinalQuoteOutput(BaseModel):
    risk_factors: list[RiskFactor]
    recommended_coverages: list[RecommendedCoverage]
    premium_range: PremiumRange
    explanation: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class FollowUpResponse(BaseModel):
    answer: str
    references: list[str] = Field(default_factory=list)
