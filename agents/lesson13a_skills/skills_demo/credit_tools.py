"""Lesson 13a: Plain Python tools, activated by the pan-credit-check skill.

These live outside the skill's own folder, on purpose. The skill folder
uses kebab-case, since that's the naming convention ADK's Skills format
expects, and it isn't a Python package. A tool a skill wants to activate
still has to be real, importable Python code, so it lives in your
project's normal module structure, and the skill's frontmatter just
references it by name.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import hashlib
import re

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def validate_pan_format(pan_number: str) -> dict:
    """Validates that a string matches the Indian PAN (Permanent Account Number) format.

    Same check used throughout this series: 5 uppercase letters, 4
    digits, 1 uppercase letter.

    Args:
        pan_number: The PAN string to validate.

    Returns:
        A dict with:
            valid (bool): True if the format matches, False otherwise.
            pan_number (str): The PAN as received, uppercased and stripped.
            error (str, optional): Present only when valid is False.
    """
    cleaned = pan_number.strip().upper()
    if PAN_PATTERN.match(cleaned):
        return {"valid": True, "pan_number": cleaned}
    return {
        "valid": False,
        "pan_number": cleaned,
        "error": f"'{cleaned}' does not match the PAN format (5 letters, 4 digits, 1 letter).",
    }


def get_credit_bureau_report(pan_number: str) -> dict:
    """Fetches a mock credit bureau report for an applicant.

    Same deterministic mock mechanism used throughout this series: a
    hash of the PAN, so the same applicant always gets the same result.

    Args:
        pan_number: The applicant's validated PAN number.

    Returns:
        A dict with:
            pan_number (str): The PAN the report was generated for.
            credit_score (int): A CIBIL-style score between 300 and 900.
            existing_loans_count (int): Number of currently active loans.
            has_defaults (bool): True if the mock history includes a default.
    """
    digest = hashlib.sha256(pan_number.encode()).hexdigest()
    seed = int(digest[:8], 16)
    return {
        "pan_number": pan_number,
        "credit_score": 300 + (seed % 601),
        "existing_loans_count": seed % 4,
        "has_defaults": (seed % 7) == 0,
    }
