"""Lesson 12: Tools for the referral agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.tools import ToolContext


def create_referral_task(
    tool_context: ToolContext,
    applicant_name: str,
    risk_band: str,
    reason: str,
) -> dict:
    """Creates a follow-up task for a senior underwriter to review a referred case.

    Writes the task directly to session state, the same reliability
    pattern used for the officer's decision itself, rather than routing
    it through this agent's own structured output.

    Args:
        tool_context: Supplied automatically by ADK.
        applicant_name: The applicant's full name.
        risk_band: "Low", "Medium", or "High", from the risk agent.
        reason: A short note on why this case needs a closer look.

    Returns:
        The referral task dict that was written to state.
    """
    task = {
        "applicant_name": applicant_name,
        "risk_band": risk_band,
        "reason": reason,
        "assigned_to": "senior_underwriting_team",
    }
    tool_context.state["referral_task"] = task
    return task
