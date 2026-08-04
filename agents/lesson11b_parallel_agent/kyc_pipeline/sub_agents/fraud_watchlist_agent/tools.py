"""Lesson 11b: Tools for the fraud watchlist agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import hashlib


def check_fraud_watchlist(applicant_name: str, pan_number: str) -> dict:
    """Screens an applicant against a mock sanctions and PEP watchlist.

    PEP (Politically Exposed Person) and sanctions list screening is a
    standard KYC requirement at every regulated bank and NBFC. This mocks
    the screen with a deterministic hash so results are repeatable, real
    screening calls out to a dedicated compliance data provider.

    Args:
        applicant_name: The applicant's full name.
        pan_number: The applicant's PAN (Permanent Account Number).

    Returns:
        A dict with:
            applicant_name (str): The name that was screened.
            pan_number (str): The PAN that was screened.
            is_flagged (bool): True if the applicant matched a watchlist entry.
            watchlist_type (str, optional): Present only when is_flagged is
                True, either "PEP" or "Sanctions List".
            error (str, optional): Present only if inputs are missing.
    """
    if not applicant_name or not pan_number:
        return {"error": "applicant_name and pan_number are both required."}

    digest = hashlib.sha256(f"{applicant_name}|{pan_number}".encode()).hexdigest()
    seed = int(digest[:8], 16)

    is_flagged = (seed % 11) == 0  # deliberately rare, most applicants clear
    watchlist_type = None
    if is_flagged:
        watchlist_type = "PEP" if seed % 2 == 0 else "Sanctions List"

    return {
        "applicant_name": applicant_name,
        "pan_number": pan_number,
        "is_flagged": is_flagged,
        "watchlist_type": watchlist_type,
    }
