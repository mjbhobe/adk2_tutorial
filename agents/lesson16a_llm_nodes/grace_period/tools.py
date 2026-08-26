"""
Lesson 16a: tools for the grace_period agent

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""


def lookup_grace_period(loan_status: str) -> dict:
    """Looks up whether a loan in this status can get a grace period.

    A plain function tool, the same kind Lesson 3 covered. Deterministic
    and synthetic, not a real lending policy lookup.

    Args:
        loan_status: The loan's current status, e.g.
            "PENDING_MANUAL_REVIEW".

    Returns:
        A dict with `eligible` and `max_days`.
    """
    if loan_status == "PENDING_MANUAL_REVIEW":
        return {"eligible": True, "max_days": 15}
    return {"eligible": False, "max_days": 0}
