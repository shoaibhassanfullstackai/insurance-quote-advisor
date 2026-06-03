from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator




class CustomerProfile(BaseModel):
    age: int = Field(..., ge=18, le=120)
    location: str = Field(..., min_length=2)
    home_value: float = Field(..., gt=0)
    has_pool: bool
    claims_history: int = Field(..., ge=0)
    credit_score: Optional[int] = Field(default=None, ge=300, le=850)

    @field_validator("location")
    @classmethod
    def normalize_location(cls, v: str) -> str:
        return v.strip().title()


class InputValidationResult(BaseModel):
    valid: bool
    profile: Optional[CustomerProfile] = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    normalized_profile: Optional[dict[str, Any]] = None
