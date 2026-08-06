"""Lesson 12: Tools for the HITL (human-in-the-loop) agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.tools import LongRunningFunctionTool


def request_officer_approval(
    applicant_name: str,
    pan_number: str,
    loan_amount: float,
    credit_score: int,
    risk_band: str,
) -> dict:
    """Submits this application for a human loan officer's review and decision.

    This is a long-running operation. Calling it does not return the
    officer's actual decision, it pauses the pipeline here. The pipeline
    resumes only when something external, a console prompt or a web
    front end, supplies a real decision (APPROVE, REJECT, or REFER) and
    the invocation is resumed. Never call this tool more than once for
    the same application, ADK marks it long-running specifically so you
    don't retry it while it's still pending.

    Args:
        applicant_name: The applicant's full name.
        pan_number: The applicant's PAN.
        loan_amount: The requested loan amount, in INR.
        credit_score: The applicant's CIBIL-style credit score.
        risk_band: "Low", "Medium", or "High", from the risk agent.

    Returns:
        A dict indicating the application is now pending officer review.
        This is a placeholder, not the officer's actual decision, that
        arrives later, asynchronously, when the pipeline is resumed.
    """
    return {
        "status": "pending_officer_review",
        "applicant_name": applicant_name,
        "pan_number": pan_number,
        "loan_amount": loan_amount,
        "credit_score": credit_score,
        "risk_band": risk_band,
    }


# Wrapping in LongRunningFunctionTool is what makes ADK pause the
# invocation here rather than waiting for this function to "finish" in
# the usual sense. See Lesson 7b for where this class was introduced.
request_officer_approval_tool = LongRunningFunctionTool(request_officer_approval)
