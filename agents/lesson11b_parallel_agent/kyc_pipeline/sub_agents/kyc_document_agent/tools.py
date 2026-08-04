"""Lesson 11b: Tools for the KYC document verification agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import hashlib
import re

# Aadhaar is India's 12-digit biometric ID, issued by UIDAI, and the most
# commonly used document for KYC address and identity verification.
AADHAAR_PATTERN = re.compile(r"^\d{12}$")


def verify_kyc_documents(applicant_name: str, date_of_birth: str, aadhaar_number: str) -> dict:
    """Verifies a KYC document (Aadhaar) against a mock records system.

    Checks the Aadhaar number's format, then simulates a match check
    against a records database using a deterministic hash. Real e-KYC
    verification calls UIDAI's own verification API rather than checking
    a local hash, this mocks that dependency for the lesson.

    Args:
        applicant_name: The applicant's full name.
        date_of_birth: The applicant's date of birth, as given in the application.
        aadhaar_number: The applicant's 12-digit Aadhaar number.

    Returns:
        A dict with:
            applicant_name (str): The name that was verified.
            aadhaar_number (str): The Aadhaar number, cleaned of spaces.
            aadhaar_valid_format (bool): True if it's 12 digits.
            documents_match (bool): True if the mock records check found a
                match. Always False when aadhaar_valid_format is False.
    """
    cleaned = aadhaar_number.strip().replace(" ", "")
    valid_format = bool(AADHAAR_PATTERN.match(cleaned))

    if not valid_format:
        return {
            "applicant_name": applicant_name,
            "aadhaar_number": cleaned,
            "aadhaar_valid_format": False,
            "documents_match": False,
        }

    digest = hashlib.sha256(f"{applicant_name}|{cleaned}|{date_of_birth}".encode()).hexdigest()
    seed = int(digest[:8], 16)
    documents_match = (seed % 9) != 0  # mostly matches, occasional mismatch

    return {
        "applicant_name": applicant_name,
        "aadhaar_number": cleaned,
        "aadhaar_valid_format": True,
        "documents_match": documents_match,
    }
