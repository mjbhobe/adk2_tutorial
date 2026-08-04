"""Lesson 11a: Credit check agent for the loan underwriting pipeline.

Reads the intake agent's output from session state, fetches a mock credit
bureau report, and writes a structured credit check result.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import get_credit_bureau_report


class CreditCheckResult(BaseModel):
    """Structured output of the credit check agent."""

    pan_number: str = Field(description="PAN the bureau report was fetched for")
    credit_score: int = Field(description="CIBIL-style score, 300 to 900")
    existing_loans_count: int = Field(description="Number of currently active loans")
    has_defaults: bool = Field(
        description="True if the bureau history shows a prior default"
    )


instruction = """You are the credit check agent for a loan underwriting pipeline at an NBFC.

The intake agent already ran. Its output is available in session state as:
{intake_result}

Read the pan_number out of it, then call the `get_credit_bureau_report` tool
with that PAN to fetch the applicant's credit bureau report. Return the
report exactly as the tool gives it back to you, in the structured fields.

Never fabricate a credit score yourself. Always call the tool.
"""

credit_check_agent = Agent(
    name="credit_check_agent",
    model=get_model("primary"),
    description="Fetches an applicant's credit bureau report using the PAN captured during intake.",
    instruction=instruction,
    tools=[get_credit_bureau_report],
    output_schema=CreditCheckResult,
    output_key="credit_check_result",
)
