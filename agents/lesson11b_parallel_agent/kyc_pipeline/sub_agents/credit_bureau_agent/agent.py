"""Lesson 11b: Credit bureau agent for KYC onboarding checks.

One of three agents that run concurrently under a ParallelAgent. Reads
the applicant's PAN directly from the original KYC application text,
there's no prior step in this pipeline to read state from.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import get_credit_bureau_report


class CreditBureauResult(BaseModel):
    """Structured output of the credit bureau agent."""

    pan_number: str = Field(description="PAN the bureau report was fetched for")
    credit_score: int = Field(description="CIBIL-style score, 300 to 900")
    existing_loans_count: int = Field(description="Number of currently active loans")
    has_defaults: bool = Field(description="True if the bureau history shows a prior default")
    total_outstanding_balance: float = Field(description="Total amount currently owed across all accounts, in INR")
    recent_enquiries_count: int = Field(description="Number of hard credit enquiries in the last 6 months")


instruction = """You are the credit bureau agent for a new customer KYC
(Know Your Customer) onboarding check at an NBFC.

A KYC application arrives as free-form text, extract the applicant's
pan_number from it, then call the `get_credit_bureau_report` tool with
that PAN. Return the report exactly as the tool gives it back to you, in
the structured fields.

Never fabricate a credit score yourself. Always call the tool.
"""

credit_bureau_agent = Agent(
    name="credit_bureau_agent",
    model=get_model("primary"),
    description="Fetches an applicant's credit bureau report during KYC onboarding.",
    instruction=instruction,
    tools=[get_credit_bureau_report],
    output_schema=CreditBureauResult,
    output_key="credit_bureau_result",
)
