"""Lesson 11a: Tools for the decision agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

# The spread a bank adds on top of its base rate for a given risk band.
# Like the base rates in the risk scoring agent, this would normally come
# from the same loan pricing engine or LMS, risk-based pricing tables get
# reviewed and adjusted by the risk team, not hardcoded into application
# code. Kept as a simple dict here for the same reason.
RISK_BAND_SPREAD = {
    "Low": 0.0,
    "Medium": 2.5,
}


def lookup_interest_rate(risk_band: str, base_interest_rate: float) -> dict:
    """Looks up the final interest rate offered for a given risk band.

    Combines the loan type's base rate (already resolved by the risk
    scoring agent) with a risk-based spread. "High" risk applicants are
    not offered a rate at all, they're rejected outright.

    Args:
        risk_band: One of "Low", "Medium", or "High".
        base_interest_rate: The loan type's base rate, as computed by the
            risk scoring agent's `calculate_risk_score` tool.

    Returns:
        A dict with:
            risk_band (str): The band that was looked up.
            eligible (bool): False for "High" risk, no rate is offered.
            interest_rate (float, optional): Final annual interest rate as
                a percentage, present only when eligible is True.
            error (str, optional): Present only for an unrecognized band.
    """
    if risk_band not in ("Low", "Medium", "High"):
        return {"error": f"Unknown risk_band '{risk_band}'."}

    if risk_band == "High":
        return {"risk_band": risk_band, "eligible": False}

    interest_rate = round(base_interest_rate + RISK_BAND_SPREAD[risk_band], 2)

    return {
        "risk_band": risk_band,
        "eligible": True,
        "interest_rate": interest_rate,
    }
