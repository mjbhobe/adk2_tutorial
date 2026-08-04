"""Lesson 11b: KYC document verification agent for onboarding checks.

One of three agents that run concurrently under a ParallelAgent. Reads
the applicant's name, date of birth, and Aadhaar number directly from
the original KYC application text, independently of the other two
branches.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import verify_kyc_documents


class KycDocumentResult(BaseModel):
    """Structured output of the KYC document verification agent."""

    applicant_name: str = Field(description="Name that was verified")
    aadhaar_number: str = Field(description="Aadhaar number, cleaned of spaces")
    aadhaar_valid_format: bool = Field(description="True if the Aadhaar number is 12 digits")
    documents_match: bool = Field(description="True if the mock records check found a match")


instruction = """You are the KYC document verification agent for a new
customer onboarding check at an NBFC.

A KYC application arrives as free-form text, extract the applicant's
applicant_name, date_of_birth, and aadhaar_number from it, then call the
`verify_kyc_documents` tool with those three values. Return the result
exactly as the tool gives it back to you, in the structured fields.

Never judge the Aadhaar format or decide on a match yourself. Always call
the tool.
"""

kyc_document_agent = Agent(
    name="kyc_document_agent",
    model=get_model("primary"),
    description="Verifies an applicant's Aadhaar document during KYC onboarding.",
    instruction=instruction,
    tools=[verify_kyc_documents],
    output_schema=KycDocumentResult,
    output_key="kyc_document_result",
)
