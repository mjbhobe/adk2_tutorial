"""Lesson 11a: Decision agent for the loan underwriting pipeline.

Reads all three prior results from session state and produces the final
loan decision.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import lookup_interest_rate


class DecisionResult(BaseModel):
    """Structured output of the decision agent."""

    decision: Literal["approved", "rejected", "refer_to_underwriter"] = Field(
        description="Final outcome of the loan application"
    )
    interest_rate: Optional[float] = Field(
        default=None,
        description="Annual interest rate offered, present only when approved",
    )
    reasons: list[str] = Field(
        description="Short, specific reasons behind the decision"
    )


instruction = """You are the decision agent, the final step in a loan
underwriting pipeline at an NBFC.

Session state has three prior results.

Intake result:
{intake_result}

Credit check result:
{credit_check_result}

Risk scoring result:
{risk_scoring_result}

Apply these rules in order:

1. If the intake result's is_complete is False, decision is
   "refer_to_underwriter". Reason: incomplete application data.
2. Otherwise, call the `lookup_interest_rate` tool with the risk_band and
   base_interest_rate from the risk scoring result.
3. If the tool reports eligible as False, decision is "rejected".
4. If the tool reports eligible as True, decision is "approved", and
   interest_rate is the rate the tool returned.

Always call the tool before approving, never guess the rate yourself. In
reasons, reference the actual loan_type, risk_band, credit_score, and
emi_to_income_ratio values you were given, not generic statements.
"""

decision_agent = Agent(
    name="decision_agent",
    model=get_model("primary"),
    description="Applies the underwriting rules and produces the final loan decision.",
    instruction=instruction,
    tools=[lookup_interest_rate],
    output_schema=DecisionResult,
    output_key="decision_result",
)
