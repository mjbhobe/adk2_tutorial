"""Lesson 11a: Tools for the risk scoring agent.

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

    Combines the bureau credit score with a rough affordability check, an
    approximate EMI (equated monthly installment) against monthly income.
    This is a teaching model, not a production underwriting formula, real
    risk models weigh many more factors and get validated by a risk team.

    Args:
        credit_score: CIBIL-style score between 300 and 900.
        annual_income: Applicant's declared annual income, in INR.
        loan_amount: Requested loan amount, in INR.
        tenure_months: Requested tenure, in months.
        has_defaults: Whether the bureau report shows a prior default.

    Returns:
        A dict with:
            risk_score (float): 0 to 100, higher means lower risk.
            risk_band (str): "Low", "Medium", or "High".
            emi_to_income_ratio (float): Approximate EMI as a fraction of
                monthly income.
            error (str, optional): Present only on invalid inputs.
    """
    if tenure_months <= 0 or annual_income <= 0:
        return {"error": "tenure_months and annual_income must both be positive."}

    credit_component = (credit_score / 900) * 60  # up to 60 points

    monthly_income = annual_income / 12
    approx_emi = loan_amount / tenure_months  # ignores interest, a deliberate simplification
    emi_to_income_ratio = round(approx_emi / monthly_income, 2)
    affordability_component = max(0.0, (1 - emi_to_income_ratio) * 40)  # up to 40 points

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
