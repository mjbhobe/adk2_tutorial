"""Lesson 11a: Risk scoring agent for the loan underwriting pipeline.

Reads the intake and credit check results from session state and produces
a deterministic risk score and band.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import calculate_risk_score


class RiskScoringResult(BaseModel):
    """Structured output of the risk scoring agent."""

    risk_score: float = Field(
        description="Risk score from 0 to 100, higher means lower risk"
    )
    risk_band: str = Field(description='One of "Low", "Medium", or "High"')
    emi_to_income_ratio: float = Field(
        description="EMI as a fraction of monthly income"
    )
    base_interest_rate: float = Field(
        description="The loan type's base interest rate used to compute the EMI"
    )


instruction = """You are the risk scoring agent for a loan underwriting pipeline at an NBFC.

Session state has two prior results.

Intake result:
{intake_result}

Credit check result:
{credit_check_result}

Pull loan_type, annual_income, loan_amount, and tenure_months from the intake
result, and credit_score plus has_defaults from the credit check result. Call
the `calculate_risk_score` tool with those six values. Return the tool's
result exactly, in the structured fields.

Always call the tool. Never estimate the score, the EMI, or the base
interest rate yourself.
"""

risk_scoring_agent = Agent(
    name="risk_scoring_agent",
    model=get_model("primary"),
    description="Calculates a deterministic risk score and band from intake and credit bureau data.",
    instruction=instruction,
    tools=[calculate_risk_score],
    output_schema=RiskScoringResult,
    output_key="risk_scoring_result",
)
