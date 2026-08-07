"""Lesson 11d: Tools for the card block agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""


def block_card(card_number: str, reason: str) -> dict:
    """Blocks a debit or credit card.

    A mock action, no real card network involved. Always succeeds.

    Args:
        card_number: The card number to block.
        reason: Why the card is being blocked, e.g. "lost" or "stolen".

    Returns:
        A dict with:
            card_number (str): The card that was blocked.
            reason (str): The reason given.
            status (str): Always "blocked" in this mock.
    """
    return {"card_number": card_number, "reason": reason, "status": "blocked"}
