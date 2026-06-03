"""Schema validation for agent JSON and light consistency checks on the final quote."""

import json
import logging
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def validate_agent_output(data: dict[str, Any], schema: Type[T]) -> tuple[bool, T | None, list[str]]:
    try:
        model = schema.model_validate(data)
        return True, model, []
    except ValidationError as e:
        msgs = [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()]
        logger.warning("Schema validation failed for %s: %s", schema.__name__, msgs)
        return False, None, msgs


def validate_final_consistency(
    risk_level: str,
    premium_low: float,
    premium_high: float,
    composite_risk: float,
) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if premium_low > premium_high:
        issues.append("premium_range.low exceeds premium_range.high")
    if premium_low < 0 or premium_high < 0:
        issues.append("premium values must be non-negative")

    # High composite risk with a very low premium band is suspicious
    if composite_risk > 0.65 and premium_high < 800:
        issues.append("premium range inconsistent with high composite risk score")

    tier_order = {"low": 0, "medium": 1, "high": 2}
    if composite_risk > 0.7 and tier_order.get(risk_level, 0) < 1:
        issues.append("overall_risk_level understates composite tool score")

    return len(issues) == 0, issues


def extract_json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)
