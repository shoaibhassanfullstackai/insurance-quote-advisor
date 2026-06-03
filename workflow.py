"""Quote pipeline orchestration via LangGraph."""

from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.graph import END, StateGraph

from agents.coverage_recommendation import CoverageRecommendationAgent
from agents.follow_up import FollowUpAgent
from agents.pricing import PricingAgent
from agents.risk_assessment import RiskAssessmentAgent
from agents.router import RouterAgent
from agents.validator import ValidatorAgent
from guardrails.input_validation import validate_customer_input
from guardrails.output_validation import validate_final_consistency
from memory.session import SessionMemory
from schemas.final_output import FinalQuoteOutput, PremiumRange, RecommendedCoverage, RiskFactor
from schemas.graph_state import QuoteGraphState
from tools.pricing_heuristic import PricingHeuristicInput, PricingHeuristicTool
from tools.risk_factor import RiskFactorInput, RiskFactorTool
from utils.confidence import compute_confidence_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class QuoteWorkflow:
    """Runs the quote graph and keeps session state for follow-ups."""

    def __init__(self) -> None:
        self.session = SessionMemory()
        self.router = RouterAgent()
        self.risk_agent = RiskAssessmentAgent()
        self.coverage_agent = CoverageRecommendationAgent()
        self.pricing_agent = PricingAgent()
        self.validator_agent = ValidatorAgent()
        self.follow_up_agent = FollowUpAgent()
        self.graph = self._build_graph()

    def _session_context_for_router(self) -> dict[str, Any]:
        return {
            "quote_completed": self.session.quote_completed,
            "has_final_quote": self.session.final_quote is not None,
            "last_user_message": self.session.last_user_message,
        }

    @staticmethod
    def _validation_rate(meta: dict[str, Any]) -> float:
        return 1.0 if meta.get("success") else 0.0

    def _build_graph(self):
        graph = StateGraph(QuoteGraphState)
        graph.add_node("router", self._node_router)
        graph.add_node("validate_input", self._node_validate_input)
        graph.add_node("risk", self._node_risk)
        graph.add_node("coverage", self._node_coverage)
        graph.add_node("pricing", self._node_pricing)
        graph.add_node("validator", self._node_validator)
        graph.add_node("assemble_quote", self._node_assemble_quote)
        graph.add_node("follow_up", self._node_follow_up)

        graph.set_entry_point("router")
        graph.add_conditional_edges(
            "router",
            self._route_after_router,
            {
                "quote_pipeline": "validate_input",
                "follow_up": "follow_up",
                "reject": END,
            },
        )
        graph.add_conditional_edges(
            "validate_input",
            lambda s: "risk" if s.get("input_valid") else END,
            {"risk": "risk"},
        )
        graph.add_edge("risk", "coverage")
        graph.add_edge("coverage", "pricing")
        graph.add_edge("pricing", "validator")
        graph.add_edge("validator", "assemble_quote")
        graph.add_edge("assemble_quote", END)
        graph.add_edge("follow_up", END)
        return graph.compile()

    def _route_after_router(self, state: QuoteGraphState) -> str:
        return state.get("route", "reject")

    def _node_router(self, state: QuoteGraphState) -> QuoteGraphState:
        user_message = state.get("user_message", "")
        self.session.last_user_message = user_message
        route_decision, route_meta = self.router.run(user_message, self._session_context_for_router())
        self.session.agent_metadata.append({"agent": "router", "meta": route_meta})

        if route_decision is None:
            return {
                "route": "reject",
                "route_reason": "Router agent failed",
                "error": "Router agent failed",
                "metadata": {"router": route_meta},
            }
        return {
            "route": route_decision.route,
            "route_reason": route_decision.reason,
            "metadata": {"router": route_meta},
        }

    def _node_validate_input(self, state: QuoteGraphState) -> QuoteGraphState:
        raw_profile = state.get("raw_profile")
        if raw_profile is None:
            user_message = state.get("user_message", "")
            try:
                raw_profile = json.loads(user_message)
            except json.JSONDecodeError:
                return {
                    "input_valid": False,
                    "input_errors": ["Provide valid customer profile JSON for a new quote"],
                    "error": "Input validation failed",
                }

        input_result = validate_customer_input(raw_profile)
        if not input_result.valid:
            return {
                "input_valid": False,
                "input_errors": input_result.errors,
                "error": "Input validation failed",
                "guardrail_total": 1,
            }

        profile = input_result.profile
        assert profile is not None
        credit_defaulted = raw_profile.get("credit_score") is None
        profile_dict = profile.model_dump()
        self.session.credit_defaulted = credit_defaulted
        self.session.input_warnings = input_result.warnings
        self.session.customer_profile = profile_dict

        return {
            "input_valid": True,
            "input_errors": [],
            "input_warnings": input_result.warnings,
            "customer_profile": profile_dict,
            "credit_defaulted": credit_defaulted,
            "guardrail_passed": 1,
            "guardrail_total": 3,
            "validation_rates": [],
        }

    def _node_risk(self, state: QuoteGraphState) -> QuoteGraphState:
        profile_dict = state["customer_profile"]
        tool_credit = profile_dict.get("credit_score", 650) or 650

        risk_tool_in = RiskFactorInput(
            location=profile_dict["location"],
            has_pool=profile_dict["has_pool"],
            claims_history=profile_dict["claims_history"],
            credit_score=tool_credit,
            home_value=profile_dict["home_value"],
            age=profile_dict["age"],
        )
        risk_tool_out = RiskFactorTool.run(risk_tool_in)
        self.session.tool_risk_breakdown = risk_tool_out.model_dump()

        risk_out, risk_meta = self.risk_agent.run(profile_dict, risk_tool_out.model_dump())
        self.session.agent_metadata.append({"agent": "risk", "meta": risk_meta})
        if risk_out is None:
            return {"error": "Risk assessment agent failed", "metadata": {"risk": risk_meta}}

        rates = list(state.get("validation_rates", []))
        rates.append(self._validation_rate(risk_meta))
        risk_dict = risk_out.model_dump()
        risk_dict["tool_breakdown"] = risk_tool_out.model_dump()
        self.session.risk_output = risk_dict

        return {
            "risk_tool_output": risk_tool_out.model_dump(),
            "risk_output": risk_dict,
            "validation_rates": rates,
        }

    def _node_coverage(self, state: QuoteGraphState) -> QuoteGraphState:
        profile_dict = state["customer_profile"]
        risk_dict = state["risk_output"]
        cov_out, cov_meta = self.coverage_agent.run(profile_dict, risk_dict)
        self.session.agent_metadata.append({"agent": "coverage", "meta": cov_meta})
        if cov_out is None:
            return {"error": "Coverage agent failed", "metadata": {"coverage": cov_meta}}

        rates = list(state.get("validation_rates", []))
        rates.append(self._validation_rate(cov_meta))
        cov_dict = cov_out.model_dump()
        self.session.coverage_output = cov_dict
        return {"coverage_output": cov_dict, "validation_rates": rates}

    def _node_pricing(self, state: QuoteGraphState) -> QuoteGraphState:
        profile_dict = state["customer_profile"]
        risk_dict = state["risk_output"]
        cov_dict = state["coverage_output"]
        risk_tool_out = state["risk_tool_output"]

        cov_mult = 1.0 + len(cov_dict["recommended_coverages"]) * 0.04
        pricing_tool_in = PricingHeuristicInput(
            home_value=profile_dict["home_value"],
            composite_risk_score=risk_tool_out["composite_score"],
            has_pool=profile_dict["has_pool"],
            claims_history=profile_dict["claims_history"],
            coverage_multiplier=min(cov_mult, 2.0),
            location=profile_dict["location"],
        )
        pricing_tool_out = PricingHeuristicTool.run(pricing_tool_in)
        self.session.tool_pricing_breakdown = pricing_tool_out.model_dump()

        price_out, price_meta = self.pricing_agent.run(
            profile_dict,
            risk_dict,
            cov_dict,
            pricing_tool_out.model_dump(),
        )
        self.session.agent_metadata.append({"agent": "pricing", "meta": price_meta})
        if price_out is None:
            return {"error": "Pricing agent failed", "metadata": {"pricing": price_meta}}

        rates = list(state.get("validation_rates", []))
        rates.append(self._validation_rate(price_meta))
        price_dict = price_out.model_dump()
        price_dict["heuristic_breakdown"] = pricing_tool_out.model_dump()
        self.session.pricing_output = price_dict
        return {
            "pricing_tool_output": pricing_tool_out.model_dump(),
            "pricing_output": price_dict,
            "validation_rates": rates,
        }

    def _node_validator(self, state: QuoteGraphState) -> QuoteGraphState:
        risk_dict = state["risk_output"]
        cov_dict = state["coverage_output"]
        price_dict = state["pricing_output"]

        val_out, val_meta = self.validator_agent.run(risk_dict, cov_dict, price_dict)
        self.session.agent_metadata.append({"agent": "validator", "meta": val_meta})
        rates = list(state.get("validation_rates", []))
        rates.append(self._validation_rate(val_meta))

        validator_consistent = True
        if val_out is None:
            validator_consistent = False
            val_dict = {"consistent": False, "issues": ["Validator agent failed"], "reasoning": ""}
        else:
            val_dict = val_out.model_dump()
            validator_consistent = val_out.consistent
        self.session.validator_output = val_dict

        consistent_ok, consistency_issues = validate_final_consistency(
            risk_level=risk_dict["overall_risk_level"],
            premium_low=price_dict["premium_range"]["low"],
            premium_high=price_dict["premium_range"]["high"],
            composite_risk=state["risk_tool_output"]["composite_score"],
        )
        guardrail_passed = state.get("guardrail_passed", 0) + (1 if consistent_ok else 0)

        return {
            "validator_output": val_dict,
            "validation_rates": rates,
            "consistency_ok": consistent_ok,
            "consistency_issues": consistency_issues,
            "guardrail_passed": guardrail_passed,
            "metadata": {"validator_consistent": validator_consistent},
        }

    def _node_assemble_quote(self, state: QuoteGraphState) -> QuoteGraphState:
        risk_dict = state["risk_output"]
        cov_dict = state["coverage_output"]
        price_dict = state["pricing_output"]
        val_dict = state["validator_output"]
        warnings = list(state.get("input_warnings", []))
        if not state.get("consistency_ok", True):
            warnings.extend(state.get("consistency_issues", []))
        if val_dict.get("issues"):
            warnings.extend(val_dict["issues"])

        explanation_parts = [
            risk_dict["reasoning"],
            cov_dict["reasoning"],
            price_dict["reasoning"],
        ]
        if val_dict.get("reasoning"):
            explanation_parts.append(val_dict["reasoning"])

        confidence = compute_confidence_score(
            agent_validation_rates=state.get("validation_rates", []),
            input_warnings_count=len(state.get("input_warnings", [])),
            guardrail_checks_passed=state.get("guardrail_passed", 0),
            guardrail_checks_total=state.get("guardrail_total", 3),
            validator_consistent=val_dict.get("consistent", False) and state.get("consistency_ok", True),
            credit_defaulted=state.get("credit_defaulted", False),
        )

        final = FinalQuoteOutput(
            risk_factors=[
                RiskFactor(
                    factor=rf["factor"],
                    severity=rf["severity"],
                    rationale=rf["rationale"],
                )
                for rf in risk_dict["risk_factors"]
            ],
            recommended_coverages=[
                RecommendedCoverage(
                    type=c["type"],
                    limit=c["limit"],
                    rationale=c["rationale"],
                )
                for c in cov_dict["recommended_coverages"]
            ],
            premium_range=PremiumRange(
                low=price_dict["premium_range"]["low"],
                high=price_dict["premium_range"]["high"],
                currency=price_dict["premium_range"]["currency"],
            ),
            explanation=" ".join(explanation_parts)[:2000],
            confidence_score=confidence,
            warnings=warnings,
        )

        self.session.final_quote = final
        self.session.quote_completed = True
        quote_result = {
            "type": "quote",
            "quote": final.model_dump(),
            "intermediate": {
                "risk": risk_dict,
                "coverage": cov_dict,
                "pricing": price_dict,
                "validator": val_dict,
            },
        }
        return {"quote_result": quote_result}

    def _node_follow_up(self, state: QuoteGraphState) -> QuoteGraphState:
        if not self.session.quote_completed:
            return {"error": "No quote in session for follow-up"}

        response, meta = self.follow_up_agent.run(
            state.get("user_message", ""),
            self.session.snapshot_for_follow_up(),
        )
        self.session.agent_metadata.append({"agent": "follow_up", "meta": meta})
        if response is None:
            return {"error": "Follow-up handler failed", "metadata": {"follow_up": meta}}

        return {
            "follow_up_output": {
                "type": "follow_up",
                "follow_up": response.model_dump(),
            }
        }

    def handle_message(self, user_message: str, profile_json: dict[str, Any] | None = None) -> dict[str, Any]:
        initial_state: QuoteGraphState = {
            "user_message": user_message,
            "raw_profile": profile_json,
            "route": "",
            "route_reason": "",
            "validation_rates": [],
            "guardrail_passed": 0,
            "guardrail_total": 3,
            "input_errors": [],
            "input_warnings": [],
            "metadata": {},
        }
        final_state = self.graph.invoke(initial_state)
        self.session.last_graph_state = dict(final_state)

        if final_state.get("error"):
            if final_state.get("input_errors"):
                return {
                    "error": final_state["error"],
                    "validation_errors": final_state.get("input_errors", []),
                    "route": final_state.get("route", "quote_pipeline"),
                }
            return {
                "error": final_state["error"],
                "metadata": final_state.get("metadata", {}),
                "route": final_state.get("route", "reject"),
            }

        if final_state.get("follow_up_output"):
            return final_state["follow_up_output"]

        if final_state.get("quote_result"):
            return final_state["quote_result"]

        return {
            "error": final_state.get("route_reason", "Request rejected by router"),
            "route": final_state.get("route", "reject"),
        }
