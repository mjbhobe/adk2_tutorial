"""Lesson 11a: Intake agent for the loan underwriting pipeline.

Validates a raw loan application, extracts structured fields, and checks
the PAN format before handing off to the credit check agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from typing import Literal

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import validate_pan_format


class IntakeResult(BaseModel):
    """Structured output of the intake agent."""

    applicant_name: str = Field(description="Full name of the loan applicant")
    pan_number: str = Field(description="Applicant's PAN (Permanent Account Number)")
    loan_type: Literal["home", "car", "personal"] = Field(
        description="Type of loan being requested"
    )
    loan_amount: float = Field(description="Requested loan amount, in INR")
    tenure_months: int = Field(description="Requested loan tenure, in months")
    annual_income: float = Field(
        description="Applicant's declared annual income, in INR"
    )
    purpose: str = Field(description="Stated purpose of the loan")
    is_complete: bool = Field(
        description="True only if every required field was present and the PAN was valid"
    )
    missing_or_invalid_fields: list[str] = Field(
        default_factory=list,
        description="Names of any fields that were missing or failed validation",
    )


instruction = """You are the intake agent for a loan underwriting pipeline at an NBFC.

A loan application arrives as free-form text. Do the following:

1. Extract these fields from the text: applicant_name, pan_number, loan_type,
   loan_amount, tenure_months, annual_income, purpose. loan_type must be
   exactly one of "home", "car", or "personal", infer it from context if the
   applicant doesn't use that exact word (a vehicle loan is "car", a home
   renovation or purchase loan is "home", anything else is "personal").
2. Call the `validate_pan_format` tool with the extracted pan_number. Never judge
   the PAN format yourself, always call the tool and use its result.
3. Set is_complete to True only if every field above was present in the
   application AND the tool reported the PAN as valid. Otherwise set it to
   False and list every missing or invalid field name in
   missing_or_invalid_fields.

Respond only with the structured fields. Do not add commentary outside them.
"""

intake_agent = Agent(
    name="intake_agent",
    model=get_model("primary"),
    description="Extracts and validates loan application fields from free-form applicant input.",
    instruction=instruction,
    tools=[validate_pan_format],
    output_schema=IntakeResult,
    output_key="intake_result",
)
