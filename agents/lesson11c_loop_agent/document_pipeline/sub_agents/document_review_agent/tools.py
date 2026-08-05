"""Lesson 11c: Tools for the document review agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import hashlib

from google.adk.tools import ToolContext


def submit_and_check_document(
    tool_context: ToolContext,
    applicant_name: str,
    aadhaar_number: str,
    attempt_number: int,
) -> dict:
    """Simulates a customer resubmitting their Aadhaar document and the system verifying it.

    In a real onboarding flow, the customer uploads a fresh photo of their
    document at this point, and the system runs OCR (Optical Character
    Recognition) plus a records match against it. Both steps are combined
    and mocked here as one deterministic call, standing in for a live
    photo upload that this lesson's single, non-interactive run can't
    wait for. A production version of this loop would pause after a
    failed attempt and resume once the next upload actually arrives,
    a human-in-the-loop pattern this series hasn't covered yet.

    Args:
        tool_context: Supplied automatically by ADK because this
            function declares a ToolContext-typed parameter. The model
            never provides this argument itself.
        applicant_name: The applicant's full name.
        aadhaar_number: The applicant's 12-digit Aadhaar number.
        attempt_number: Which attempt this is, 1 for the first submission.

    Returns:
        A dict with:
            attempt_number (int): Echoes the attempt number passed in.
            passed (bool): True if this submission cleared verification.
            issue (str, optional): Present only when passed is False, a
                short description of what went wrong.
    """

    digest = hashlib.sha256(
        f"{applicant_name}|{aadhaar_number}|{attempt_number}".encode()
    ).hexdigest()
    seed = int(digest[:8], 16)

    passed = (seed % 3) != 0  # roughly 2 in 3 attempts pass, independently each time

    if passed:
        return {"attempt_number": attempt_number, "passed": True}

    issues = [
        "Image too blurry to read",
        "Document appears expired",
        "Name does not match application",
    ]

    # signal to ADK to exit loop
    tool_context.actions.escalate = True
    return {
        "attempt_number": attempt_number,
        "passed": False,
        "issue": issues[seed % len(issues)],
    }


def exit_document_loop(tool_context: ToolContext) -> dict:
    """Signals that the document retry loop should stop, verification passed.

    Sets escalate on the tool context's actions. LoopAgent checks this
    flag after every event its sub-agents produce, and stops repeating as
    soon as it sees escalate set to True, rather than waiting for
    max_iterations.

    Args:
        tool_context: Supplied automatically by ADK because this
            function declares a ToolContext-typed parameter. The model
            never provides this argument itself.

    Returns:
        A short acknowledgement dict.
    """
    tool_context.actions.escalate = True
    return {"status": "loop_exit_requested"}
