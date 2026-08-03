"""Lesson 11a: Tools for the credit check agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import hashlib


def get_credit_bureau_report(pan_number: str) -> dict:
    """Fetches a mock credit bureau report for an applicant.

    This simulates a call to a credit bureau (like CIBIL) using a
    deterministic hash of the PAN, so the same applicant always gets the
    same mock score. That makes the pipeline repeatable while you're
    learning. Swap this out for a real bureau API integration in production.

    Args:
        pan_number: The applicant's validated PAN number.

    Returns:
        A dict with:
            pan_number (str): The PAN the report was generated for.
            credit_score (int): A CIBIL-style score between 300 and 900.
            existing_loans_count (int): Number of currently active loans.
            has_defaults (bool): True if the mock history includes a default.
            error (str, optional): Present only if pan_number is empty.
    """
    if not pan_number:
        return {"error": "pan_number is required to fetch a credit bureau report."}

    digest = hashlib.sha256(pan_number.encode()).hexdigest()
    seed = int(digest[:8], 16)

    credit_score = 300 + (seed % 601)  # 300 to 900
    existing_loans_count = seed % 4  # 0 to 3
    has_defaults = (seed % 7) == 0  # roughly 1 in 7 applicants

    return {
        "pan_number": pan_number,
        "credit_score": credit_score,
        "existing_loans_count": existing_loans_count,
        "has_defaults": has_defaults,
    }
