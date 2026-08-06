"""Lesson 12: Credit agent, the first step of the loan approval pipeline.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import get_credit_bureau_report, validate_pan_format


class CreditResult(BaseModel):
    """Structured output of the credit agent."""

    applicant_name: str = Field(description="Full name of the loan applicant")
    pan_number: str = Field(description="Applicant's PAN (Permanent Account Number)")
    loan_amount: float = Field(description="Requested loan amount, in INR")
    tenure_months: int = Field(description="Requested loan tenure, in months")
    annual_income: float = Field(
        description="Applicant's declared annual income, in INR"
    )
    credit_score: int = Field(description="CIBIL-style score, 300 to 900")
    existing_loans_count: int = Field(description="Number of currently active loans")
    has_defaults: bool = Field(
        description="True if the bureau history shows a prior default"
    )


instruction = """You are the credit agent for a loan approval pipeline at
a retail bank.

A loan application arrives as free-form text. Do the following:

1. Extract applicant_name, pan_number, loan_amount, tenure_months, and
   annual_income from it.
2. Call `validate_pan_format` with the extracted pan_number.
3. Call `get_credit_bureau_report` with the validated pan_number.

Respond with the structured fields, combining what you extracted with
what the credit bureau tool returned. Always call both tools, never
fabricate a credit score yourself.
"""

credit_agent = Agent(
    name="credit_agent",
    model=get_model("primary"),
    description="Extracts loan application fields and fetches the applicant's credit bureau report.",
    instruction=instruction,
    tools=[validate_pan_format, get_credit_bureau_report],
    output_schema=CreditResult,
    output_key="credit_result",
)
