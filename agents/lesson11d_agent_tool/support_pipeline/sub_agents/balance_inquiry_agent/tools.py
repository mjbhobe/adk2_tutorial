"""Lesson 11d: Tools for the balance inquiry agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import hashlib


def get_account_balance(account_number: str) -> dict:
    """Fetches a mock account balance.

    Deterministic hash of the account number, so the same account
    always shows the same balance.

    Args:
        account_number: The customer's account number.

    Returns:
        A dict with:
            account_number (str): The account that was checked.
            balance (float): The current balance, in INR.
    """
    digest = hashlib.sha256(account_number.encode()).hexdigest()
    seed = int(digest[:8], 16)
    return {"account_number": account_number, "balance": float(seed % 500000)}
