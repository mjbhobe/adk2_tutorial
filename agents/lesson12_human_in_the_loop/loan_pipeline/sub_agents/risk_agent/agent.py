"""Lesson 12: Risk agent, the second step of the loan approval pipeline.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import calculate_risk_score


class RiskResult(BaseModel):
    """Structured output of the risk agent."""

    risk_score: float = Field(
        description="Risk score from 0 to 100, higher means lower risk"
    )
    risk_band: str = Field(description='One of "Low", "Medium", or "High"')
    emi_to_income_ratio: float = Field(
        description="EMI as a fraction of monthly income"
    )


instruction = """You are the risk agent for a loan approval pipeline at a
retail bank.

Session state has the credit agent's result:
{credit_result}

Pull credit_score, annual_income, loan_amount, tenure_months, and
has_defaults from it, and call `calculate_risk_score` with those five
values. Return the tool's result exactly, in the structured fields.

Always call the tool. Never estimate the score yourself.
"""

risk_agent = Agent(
    name="risk_agent",
    model=get_model("primary"),
    description="Calculates a deterministic risk score and band from the credit agent's findings.",
    instruction=instruction,
    tools=[calculate_risk_score],
    output_schema=RiskResult,
    output_key="risk_result",
)
