"""Lesson 11b: Fraud watchlist agent for KYC onboarding checks.

One of three agents that run concurrently under a ParallelAgent. Reads
the applicant's name and PAN directly from the original KYC application
text, independently of the other two branches.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from typing import Optional

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import check_fraud_watchlist


class FraudWatchlistResult(BaseModel):
    """Structured output of the fraud watchlist agent."""

    applicant_name: str = Field(description="Name that was screened")
    pan_number: str = Field(description="PAN that was screened")
    is_flagged: bool = Field(description="True if the applicant matched a watchlist entry")
    watchlist_type: Optional[str] = Field(
        default=None, description='Either "PEP" or "Sanctions List", present only when flagged'
    )


instruction = """You are the fraud watchlist agent for a new customer KYC
(Know Your Customer) onboarding check at an NBFC.

A KYC application arrives as free-form text, extract the applicant's
applicant_name and pan_number from it, then call the
`check_fraud_watchlist` tool with those two values. Return the result
exactly as the tool gives it back to you, in the structured fields.

Never decide whether someone is flagged yourself. Always call the tool.
"""

fraud_watchlist_agent = Agent(
    name="fraud_watchlist_agent",
    model=get_model("primary"),
    description="Screens an applicant against sanctions and PEP watchlists during KYC onboarding.",
    instruction=instruction,
    tools=[check_fraud_watchlist],
    output_schema=FraudWatchlistResult,
    output_key="fraud_watchlist_result",
)
