"""Confidence on the final quote from validation and completeness signals."""

from typing import Any


def compute_confidence_score(
    *,
    agent_validation_rates: list[float],
    input_warnings_count: int,
    guardrail_checks_passed: int,
    guardrail_checks_total: int,
    validator_consistent: bool,
    credit_defaulted: bool,
) -> float:
    """
    Weighted score (0–1), not model self-assessment:
    50% agent validation success, 30% input/consistency checks, 20% data completeness.
    """
    if not agent_validation_rates:
        agent_avg = 0.0
    else:
        agent_avg = sum(agent_validation_rates) / len(agent_validation_rates)

    guardrail_rate = (
        guardrail_checks_passed / guardrail_checks_total
        if guardrail_checks_total > 0
        else 0.0
    )

    completeness = 1.0
    if credit_defaulted:
        completeness -= 0.15
    if input_warnings_count > 0:
        completeness -= min(0.1 * input_warnings_count, 0.25)
    if not validator_consistent:
        completeness -= 0.2
    completeness = max(0.0, completeness)

    score = 0.5 * agent_avg + 0.3 * guardrail_rate + 0.2 * completeness
    return round(min(1.0, max(0.0, score)), 3)
