"""Lesson 11a: Tools for the decision agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

_RATE_CARD = {
    "Low": 10.5,
    "Medium": 13.5,
}


def lookup_interest_rate(risk_band: str) -> dict:
    """Looks up the interest rate offered for a given risk band.

    A stand-in for a real rate card lookup. In production this would read
    from a pricing service that moves with market conditions, not a fixed
    dict.

    Args:
        risk_band: One of "Low", "Medium", or "High".

    Returns:
        A dict with:
            risk_band (str): The band that was looked up.
            eligible (bool): False for "High" risk, no rate is offered.
            interest_rate (float, optional): Annual interest rate as a
                percentage, present only when eligible is True.
            error (str, optional): Present only for an unrecognized band.
    """
    if risk_band not in ("Low", "Medium", "High"):
        return {"error": f"Unknown risk_band '{risk_band}'."}

    if risk_band == "High":
        return {"risk_band": risk_band, "eligible": False}

    return {
        "risk_band": risk_band,
        "eligible": True,
        "interest_rate": _RATE_CARD[risk_band],
    }
