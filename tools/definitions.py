"""JSON schemas for tools (function-calling shape). Invoked from workflow nodes, not via MCP."""

from tools.pricing_heuristic import PricingHeuristicTool
from tools.risk_factor import RiskFactorTool

RISK_FACTOR_TOOL_DEFINITION = {
    "name": RiskFactorTool.name,
    "description": RiskFactorTool.description,
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {"type": "string"},
            "has_pool": {"type": "boolean"},
            "claims_history": {"type": "integer", "minimum": 0},
            "credit_score": {"type": ["integer", "null"], "minimum": 300, "maximum": 850},
            "home_value": {"type": "number", "exclusiveMinimum": 0},
            "age": {"type": "integer", "minimum": 18, "maximum": 120},
        },
        "required": ["location", "has_pool", "claims_history", "home_value", "age"],
    },
}

PRICING_HEURISTIC_TOOL_DEFINITION = {
    "name": PricingHeuristicTool.name,
    "description": PricingHeuristicTool.description,
    "input_schema": {
        "type": "object",
        "properties": {
            "home_value": {"type": "number", "exclusiveMinimum": 0},
            "composite_risk_score": {"type": "number", "minimum": 0, "maximum": 1},
            "has_pool": {"type": "boolean"},
            "claims_history": {"type": "integer", "minimum": 0},
            "coverage_multiplier": {"type": "number", "minimum": 0.5, "maximum": 2.5},
            "location": {"type": "string"},
        },
        "required": [
            "home_value",
            "composite_risk_score",
            "has_pool",
            "claims_history",
            "location",
        ],
    },
}

ALL_TOOL_DEFINITIONS = [
    RISK_FACTOR_TOOL_DEFINITION,
    PRICING_HEURISTIC_TOOL_DEFINITION,
]
