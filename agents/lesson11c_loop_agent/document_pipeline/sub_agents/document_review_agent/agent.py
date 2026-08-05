"""Lesson 11c: Document review agent, the sub-agent LoopAgent repeats.

Each time LoopAgent runs this agent, it's one attempt at verifying the
applicant's Aadhaar document. It tracks the attempt number through its
own previous result in session state, and calls exit_document_loop only
once verification actually passes, letting LoopAgent's max_iterations
act as the safety net for the case where it never does.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from typing import Optional

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import submit_and_check_document  # , exit_document_loop


class DocumentCheckResult(BaseModel):
    """Structured output of the document review agent, written every attempt."""

    attempt_number: int = Field(
        description="Which attempt this was, 1 for the first submission"
    )
    passed: bool = Field(description="True if this submission cleared verification")
    issue: Optional[str] = Field(
        default=None, description="Present only when passed is False"
    )


instruction = """You are the document review agent for a KYC (Know Your
Customer) onboarding check at an NBFC. Your job is to verify an
applicant's Aadhaar document, one attempt per turn, retrying automatically
until it passes or the retry limit is reached.

The applicant's name and Aadhaar number are in the original request.
Session state may already hold a result from an earlier attempt:
{document_check_result?}

If document_check_result is present, this is a retry, use its
attempt_number plus 1 as this attempt's number. If it's not present,
this is the first attempt, attempt_number is 1.

1. Call `submit_and_check_document` with applicant_name, aadhaar_number,
   and this attempt's attempt_number.
3. Respond with the structured fields, echoing exactly what
   `submit_and_check_document` returned.

Respond with the structured fields only. No markdown, no headers, no
commentary, just the fields the schema requires.
"""

document_review_agent = Agent(
    name="document_review_agent",
    # model=get_model("primary"),
    # model=get_model("escalation"),
    model="gemini-3.6-flash",
    description="Verifies an applicant's Aadhaar document, one attempt per turn, signaling exit once it passes.",
    instruction=instruction,
    # tools=[submit_and_check_document, exit_document_loop],
    tools=[submit_and_check_document],
    output_schema=DocumentCheckResult,
    output_key="document_check_result",
)
