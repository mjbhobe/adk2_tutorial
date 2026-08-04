"""Lesson 11b: KYC decision agent, the merge step after the parallel checks.

Reads all three parallel checks' results from session state and applies
the onboarding decision rules. This is the step that gives the
ParallelAgent's fan-out somewhere to land, three independent checks are
only useful if something downstream actually does something with all
three together.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from typing import Literal

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import make_kyc_decision


class KycDecisionResult(BaseModel):
    """Structured output of the KYC decision agent."""

    decision: Literal["approved", "manual_review", "rejected"] = Field(
        description="Final outcome of the KYC onboarding check"
    )
    reasons: list[str] = Field(description="Every rule that contributed to the decision")


instruction = """You are the KYC decision agent, the final step in a new
customer onboarding check at an NBFC.

Session state has three results, written concurrently by the credit
bureau, fraud watchlist, and KYC document checks that ran before you.

Fraud watchlist result:
{fraud_watchlist_result}

KYC document result:
{kyc_document_result}

Credit bureau result:
{credit_bureau_result}

Pull is_flagged and watchlist_type from the fraud watchlist result,
aadhaar_valid_format and documents_match from the KYC document result,
and has_defaults and recent_enquiries_count from the credit bureau
result. Call the `make_kyc_decision` tool with those six values. Return
the tool's result exactly, in the structured fields.

Always call the tool. Never decide the outcome yourself.
"""

kyc_decision_agent = Agent(
    name="kyc_decision_agent",
    model=get_model("primary"),
    description="Applies the onboarding decision rules to the three parallel checks' results.",
    instruction=instruction,
    tools=[make_kyc_decision],
    output_schema=KycDecisionResult,
    output_key="kyc_decision_result",
)
