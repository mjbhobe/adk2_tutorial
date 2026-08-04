"""Lesson 11a: Tools for the risk scoring agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

# In production, base interest rates come from the bank's loan pricing
# engine or loan management system (LMS), for example Finacle, or a
# dedicated rates microservice, not a hardcoded dict. Rates there change
# with market conditions, funding cost, and product-level pricing
# decisions, sometimes daily. Query that service by loan_type (and often
# tenure and loan amount slab too) rather than baking rates into agent
# code. This dict is a stand-in for that lookup, so the lesson doesn't
# depend on a rates service that doesn't exist for it.
BASE_INTEREST_RATES = {
    "home": 8.5,
    "car": 7.5,
    "personal": 10.5,
}


def calculate_emi(loan_amount: float, annual_rate: float, tenure_months: int) -> float:
    """Calculates the standard amortized EMI for a loan.

    Uses the standard reducing-balance EMI formula:
    EMI = P * r * (1 + r)^n / ((1 + r)^n - 1), where r is the monthly
    interest rate and n is the tenure in months.

    Args:
        loan_amount: Principal amount, in INR.
        annual_rate: Annual interest rate, as a percentage (e.g. 8.5 for 8.5%).
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
    loan_type: str,
    credit_score: int,
    annual_income: float,
    loan_amount: float,
    tenure_months: int,
    has_defaults: bool,
) -> dict:
    """Calculates a deterministic risk score for a loan application.

    Combines the bureau credit score with an affordability check based on
    the actual amortized EMI for this loan type's base interest rate. This
    is a teaching model, not a production underwriting formula, real risk
    models weigh many more factors and get validated by a risk team.

    Args:
        loan_type: One of "home", "car", or "personal".
        credit_score: CIBIL-style score between 300 and 900.
        annual_income: Applicant's declared annual income, in INR.
        loan_amount: Requested loan amount, in INR.
        tenure_months: Requested tenure, in months.
        has_defaults: Whether the bureau report shows a prior default.

    Returns:
        A dict with:
            risk_score (float): 0 to 100, higher means lower risk.
            risk_band (str): "Low", "Medium", or "High".
            emi_to_income_ratio (float): EMI as a fraction of monthly income.
            base_interest_rate (float): The loan type's base rate used for
                this calculation.
            error (str, optional): Present only on invalid inputs.
    """
    if loan_type not in BASE_INTEREST_RATES:
        return {"error": f"Unknown loan_type '{loan_type}'."}
    if tenure_months <= 0 or annual_income <= 0:
        return {"error": "tenure_months and annual_income must both be positive."}

    base_interest_rate = BASE_INTEREST_RATES[loan_type]

    credit_component = (credit_score / 900) * 60  # up to 60 points

    monthly_income = annual_income / 12
    emi = calculate_emi(loan_amount, base_interest_rate, tenure_months)
    emi_to_income_ratio = round(emi / monthly_income, 2)
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
        "base_interest_rate": base_interest_rate,
    }
