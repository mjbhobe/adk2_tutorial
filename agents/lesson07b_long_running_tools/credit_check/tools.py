"""Lesson 7b: Long-Running Tools — credit bureau check tool."""

import time

from google.adk.tools import LongRunningFunctionTool


def run_credit_bureau_check(
    applicant_id: str,
    requested_loan_amount: float,
) -> dict:
    """Initiates a credit bureau check for a loan applicant.

    This is a long-running operation: in a real system, the credit
    bureau API accepts the request and responds asynchronously,
    typically 15 to 60 seconds. The sleep here simulates that latency
    so the lesson runs without real external calls.

    The framework automatically appends a note to this tool's
    description telling the model not to call it again while it is
    already in progress. You do not need to write that note yourself.

    Args:
        applicant_id: The bank's unique identifier for this applicant.
        requested_loan_amount: The loan amount being applied for.

    Returns:
        A dict with the credit score, band, existing obligations, and
        the maximum recommended new loan amount.
    """
    # Simulate the bureau taking a few seconds to respond.
    # In production this would be a real API call with async polling.
    time.sleep(3)

    return {
        "applicant_id": applicant_id,
        "status": "complete",
        "credit_score": 742,
        "credit_band": "Good",
        "total_existing_obligations": 45000.0,
        "recommended_max_new_loan": min(requested_loan_amount, 2500000.0),
        "bureau": "CIBIL",
    }


# Wrap the plain function in LongRunningFunctionTool instead of
# leaving it as a bare function. This is the only change from how
# you'd define a regular function tool in Lesson 3. The function
# itself is identical — no special return type, no generator protocol.
credit_bureau_check = LongRunningFunctionTool(run_credit_bureau_check)
