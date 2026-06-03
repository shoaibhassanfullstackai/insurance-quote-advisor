"""Validate customer profiles before the quote pipeline runs."""

from typing import Any

from pydantic import ValidationError

from schemas.customer_profile import CustomerProfile, InputValidationResult

REQUIRED_FIELDS = ("age", "location", "home_value", "has_pool", "claims_history")


def validate_customer_input(raw: dict[str, Any]) -> InputValidationResult:
    warnings: list[str] = []
    errors: list[str] = []

    if not isinstance(raw, dict):
        return InputValidationResult(
            valid=False,
            errors=["Input must be a JSON object"],
        )

    missing = [f for f in REQUIRED_FIELDS if f not in raw]
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    if errors:
        return InputValidationResult(valid=False, errors=errors, warnings=warnings)

    normalized = dict(raw)
    if normalized.get("credit_score") is None:
        warnings.append(
            "credit_score missing; using 650 for risk/pricing tools"
        )
        normalized["_credit_defaulted"] = True

    try:
        profile = CustomerProfile(
            age=normalized["age"],
            location=str(normalized["location"]),
            home_value=float(normalized["home_value"]),
            has_pool=bool(normalized["has_pool"]),
            claims_history=int(normalized["claims_history"]),
            credit_score=normalized.get("credit_score"),
        )
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            errors.append(f"{loc}: {err['msg']}")
        return InputValidationResult(valid=False, errors=errors, warnings=warnings)

    if profile.home_value > 5_000_000:
        warnings.append("home_value exceeds typical underwriting band; quote may be capped")

    return InputValidationResult(
        valid=True,
        profile=profile,
        warnings=warnings,
        normalized_profile=profile.model_dump(),
    )
