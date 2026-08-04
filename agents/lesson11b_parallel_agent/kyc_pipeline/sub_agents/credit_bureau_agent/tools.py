"""Lesson 11b: Tools for the credit bureau agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import hashlib


def get_credit_bureau_report(pan_number: str) -> dict:
    """Fetches a mock credit bureau report for an applicant.

    Same mock mechanism as Lesson 11a's credit check agent: a deterministic
    hash of the PAN, so the same applicant always gets the same result.
    Swap this out for a real bureau API integration in production.

    Args:
        pan_number: The applicant's PAN (Permanent Account Number).

    Returns:
        A dict with:
            pan_number (str): The PAN the report was generated for.
            credit_score (int): A CIBIL-style score between 300 and 900.
            existing_loans_count (int): Number of currently active loans.
            has_defaults (bool): True if the mock history includes a default.
            total_outstanding_balance (float): Total amount currently owed
                across all accounts, in INR.
            recent_enquiries_count (int): Number of hard credit enquiries
                (loan or credit card applications) in the last 6 months.
                A high count is a real risk signal lenders watch for,
                sometimes called "credit hungry" behavior.
            error (str, optional): Present only if pan_number is empty.
    """
    if not pan_number:
        return {"error": "pan_number is required to fetch a credit bureau report."}

    digest = hashlib.sha256(pan_number.encode()).hexdigest()
    seed = int(digest[:8], 16)

    return {
        "pan_number": pan_number,
        "credit_score": 300 + (seed % 601),
        "existing_loans_count": seed % 4,
        "has_defaults": (seed % 7) == 0,
        "total_outstanding_balance": float(seed % 2000000),
        "recent_enquiries_count": seed % 6,
    }
