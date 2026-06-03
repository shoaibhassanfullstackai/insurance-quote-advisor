import bootstrap  # noqa: F401

from guardrails.input_validation import validate_customer_input
from tools.pricing_heuristic import PricingHeuristicInput, PricingHeuristicTool
from tools.risk_factor import RiskFactorInput, RiskFactorTool


def test_risk_factor_tool():
    inp = RiskFactorInput(
        location="California",
        has_pool=True,
        claims_history=1,
        credit_score=700,
        home_value=900000,
        age=50,
    )
    out = RiskFactorTool.run(inp)
    assert 0 <= out.composite_score <= 1
    assert out.overall_tier in ("low", "medium", "high")
    assert len(out.dimensions) >= 5


def test_pricing_heuristic_tool():
    inp = PricingHeuristicInput(
        home_value=900000,
        composite_risk_score=0.6,
        has_pool=True,
        claims_history=1,
        location="California",
    )
    out = PricingHeuristicTool.run(inp)
    assert out.low <= out.high
    assert out.currency == "USD"


def test_missing_credit_score():
    raw = {
        "age": 34,
        "location": "Florida",
        "home_value": 450000,
        "has_pool": False,
        "claims_history": 0,
        "credit_score": None,
    }
    result = validate_customer_input(raw)
    assert result.valid
    assert any("credit_score" in w for w in result.warnings)


if __name__ == "__main__":
    test_risk_factor_tool()
    test_pricing_heuristic_tool()
    test_missing_credit_score()
    print("ok")
