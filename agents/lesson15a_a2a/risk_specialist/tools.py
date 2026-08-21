"""Lesson 15a: The risk-scoring tool, reused unchanged from 13a.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""


def calculate_risk_score(
    credit_score: int,
    annual_income: float,
    loan_amount: float,
    tenure_months: int,
    has_defaults: bool,
) -> dict:
    """Calculates a deterministic risk score for a loan application.

    Args:
        credit_score: CIBIL-style score between 300 and 900.
        annual_income: Applicant's declared annual income, in INR.
        loan_amount: Requested loan amount, in INR.
        tenure_months: Requested tenure, in months.
        has_defaults: Whether the credit report shows a prior default.

    Returns:
        A dict with risk_score, risk_band, and emi_to_income_ratio.
    """
    score = credit_score / 900 * 60
    if has_defaults:
        score -= 25
    monthly_income = annual_income / 12
    emi_estimate = loan_amount / tenure_months
    ratio = round(emi_estimate / monthly_income, 4) if monthly_income else 1.0
    score -= min(ratio * 40, 40)
    score = max(0, min(100, round(score, 1)))

    if score >= 70:
        band = "Low"
    elif score >= 40:
        band = "Medium"
    else:
        band = "High"

    return {"risk_score": score, "risk_band": band, "emi_to_income_ratio": ratio}
