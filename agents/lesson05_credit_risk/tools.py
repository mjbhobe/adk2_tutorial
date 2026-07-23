"""
Debt-to-income calculation for the credit risk assessment agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""


def calculate_debt_to_income_ratio(
    monthly_income: float,
    total_monthly_debt_payments: float,
) -> dict:
    """Calculates a debt-to-income (DTI) ratio, a standard credit risk metric.

    DTI is one of the most widely used inputs in retail credit
    underwriting: it measures what share of a borrower's income is
    already committed to debt payments before any new loan.

    Args:
        monthly_income: The applicant's gross monthly income.
        total_monthly_debt_payments: The sum of all the applicant's
            existing monthly debt obligations, including any loan
            they're currently applying for on top of that.

    Returns:
        A dict with the DTI ratio as a percentage, or an error if the
        income given was zero or negative.
    """
    if monthly_income <= 0:
        return {"error": "monthly_income must be a positive number."}

    dti_percent = (total_monthly_debt_payments / monthly_income) * 100

    return {
        "debt_to_income_ratio_percent": round(dti_percent, 2),
        "monthly_income": monthly_income,
        "total_monthly_debt_payments": total_monthly_debt_payments,
    }
