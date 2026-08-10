"""Lesson 13a: Tools for the risk specialist agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""


def calculate_emi(loan_amount: float, annual_rate: float, tenure_months: int) -> float:
    """Calculates the standard amortized EMI for a loan.

    Same reducing-balance formula used throughout this series.

    Args:
        loan_amount: Principal amount, in INR.
        annual_rate: Annual interest rate, as a percentage.
        tenure_months: Loan tenure, in months.

    Returns:
        The monthly EMI, in INR.
    """
    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        return loan_amount / tenure_months
    growth_factor = (1 + monthly_rate) ** tenure_months
    return loan_amount * monthly_rate * growth_factor / (growth_factor - 1)


def calculate_risk_score(
    credit_score: int,
    annual_income: float,
    loan_amount: float,
    tenure_months: int,
    has_defaults: bool,
) -> dict:
    """Calculates a deterministic risk score for a loan application.

    Same formula shape as Lesson 11a and 12: up to 60 points from the
    credit score, up to 40 from affordability, minus a 25-point penalty
    for a prior default. Uses a flat 10.5% assumed rate for the
    affordability check, matching Lesson 12's risk agent.

    Args:
        credit_score: CIBIL-style score between 300 and 900.
        annual_income: Applicant's declared annual income, in INR.
        loan_amount: Requested loan amount, in INR.
        tenure_months: Requested tenure, in months.
        has_defaults: Whether the credit report shows a prior default.

    Returns:
        A dict with:
            risk_score (float): 0 to 100, higher means lower risk.
            risk_band (str): "Low", "Medium", or "High".
            emi_to_income_ratio (float): EMI as a fraction of monthly income.
    """
    credit_component = (credit_score / 900) * 60

    monthly_income = annual_income / 12
    emi = calculate_emi(loan_amount, 10.5, tenure_months)
    emi_to_income_ratio = round(emi / monthly_income, 2)
    affordability_component = max(0.0, (1 - emi_to_income_ratio) * 40)

    risk_score = credit_component + affordability_component
    if has_defaults:
        risk_score -= 25

    risk_score = round(max(0.0, min(100.0, risk_score)), 1)

    if risk_score >= 70:
        risk_band = "Low"
    elif risk_score >= 45:
        risk_band = "Medium"
    else:
        risk_band = "High"

    return {
        "risk_score": risk_score,
        "risk_band": risk_band,
        "emi_to_income_ratio": emi_to_income_ratio,
    }
