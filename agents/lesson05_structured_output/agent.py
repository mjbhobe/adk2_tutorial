"""Lesson 5: Structured Output.

A credit risk assessment agent for a retail bank's underwriting desk.
It calls a tool to compute a real debt-to-income ratio, then returns
its verdict as a validated, fixed-shape JSON object rather than free
text, so the result can be written straight into an approval system
without manual re-entry.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from typing import Literal

from google.adk.agents import Agent
from pydantic import BaseModel, Field

from common.model_config import get_model
from .tools import calculate_debt_to_income_ratio


class CreditRiskAssessment(BaseModel):
    """The fixed shape every underwriting verdict from this agent must match."""

    risk_tier: Literal["Low", "Medium", "High"] = Field(
        description="The applicant's overall credit risk tier."
    )
    is_recommended_for_approval: bool = Field(
        description="Whether the agent recommends approving this application."
    )
    max_recommended_loan_amount: float = Field(
        description=(
            "The maximum loan amount the agent recommends approving for "
            "this applicant, given their income and existing obligations."
        )
    )
    key_risk_factors: list[str] = Field(
        description=(
            "Specific factors driving the risk tier, e.g. 'high "
            "debt-to-income ratio' or 'limited credit history'."
        )
    )
    rationale: str = Field(
        description="A short, plain-language explanation of the assessment."
    )


AGENT_INSTRUCTION = (
    "You are a credit risk assessment assistant for a retail bank's "
    "underwriting desk. Given an applicant's financial details, use "
    "the calculate_debt_to_income_ratio tool to compute their DTI "
    "before forming a judgment; never estimate this ratio yourself. "
    "As a general guideline, a DTI under 35% is typically Low risk, "
    "35-45% is typically Medium risk, and above 45% is typically High "
    "risk, though you should weigh other details the applicant "
    "mentions, such as employment stability or credit history, "
    "alongside the DTI rather than relying on it alone. Always "
    "provide specific, concrete risk factors, not vague statements."
)

root_agent = Agent(
    name="credit_risk_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description=(
        "Assesses retail loan applicant credit risk and returns a "
        "structured, validated verdict for the underwriting desk."
    ),
    tools=[calculate_debt_to_income_ratio],
    output_schema=CreditRiskAssessment,
    # uncomment following like to also write the structured
    # output to session state at key "latest_credit_assessment"
    # output_key="latest_credit_assessment",
)
