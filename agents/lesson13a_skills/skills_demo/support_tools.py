"""Lesson 13a: An always-available tool, not gated behind any skill.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import hashlib


def record_customer_query(query_summary: str, category: str) -> dict:
    """Logs a customer interaction for compliance and audit purposes.

    Every customer interaction gets logged, regardless of which skill,
    if any, handled it. That's exactly why this is a plain tool sitting
    directly in the agent's own tools list, not something gated behind
    a skill's activation state.

    Args:
        query_summary: A short summary of what the customer asked.
        category: One of "pan_credit", "emi", "risk", or "general".

    Returns:
        A dict with:
            logged (bool): Always True in this mock.
            reference_id (str): A mock audit reference for this entry.
            category (str): Echoes the category given.
    """
    digest = hashlib.sha256(f"{query_summary}|{category}".encode()).hexdigest()
    reference_id = digest[:8].upper()
    return {"logged": True, "reference_id": reference_id, "category": category}
