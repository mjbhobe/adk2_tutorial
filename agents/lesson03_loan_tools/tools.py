"""Loan calculator tools for the retail lending desk agent.

Each function here is a plain, typed Python function with no
dependency on ADK. That's deliberate: a tool function should be
testable and usable on its own, with ADK only responsible for
exposing it to the model, not for how it works internally.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""


def calculate_emi(
    principal: float,
    annual_interest_rate_percent: float,
    tenure_months: int,
) -> dict:
    """Calculates the monthly EMI for a loan using the standard amortization formula.

    Args:
        principal: The loan amount being borrowed, in the local currency.
        annual_interest_rate_percent: The annual interest rate as a
            percentage, for example 8.5 for 8.5%.
        tenure_months: The loan repayment period in months.

    Returns:
        A dict with the monthly EMI, total amount payable over the
        loan's life, and total interest paid.
    """
    monthly_rate = (annual_interest_rate_percent / 100) / 12

    if monthly_rate == 0:
        emi = principal / tenure_months
    else:
        growth_factor = (1 + monthly_rate) ** tenure_months
        emi = principal * monthly_rate * growth_factor / (growth_factor - 1)

    total_payment = emi * tenure_months
    total_interest = total_payment - principal

    return {
        "monthly_emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
        "principal": principal,
        "tenure_months": tenure_months,
        "annual_interest_rate_percent": annual_interest_rate_percent,
    }


def check_loan_affordability(
    monthly_income: float,
    existing_monthly_emis: float,
    annual_interest_rate_percent: float,
    tenure_months: int,
    max_foir_percent: float = 50.0,
) -> dict:
    """Estimates the maximum loan a customer can afford given their income.

    Uses FOIR (Fixed Obligation to Income Ratio), a standard lending
    guardrail that caps total monthly loan obligations as a percentage
    of monthly income. Most retail lenders use a FOIR ceiling between
    40 and 50 percent.

    Args:
        monthly_income: The customer's gross monthly income.
        existing_monthly_emis: The sum of all EMIs the customer is
            already paying on other loans.
        annual_interest_rate_percent: The annual interest rate the new
            loan would carry, as a percentage.
        tenure_months: The proposed repayment period for the new loan,
            in months.
        max_foir_percent: The maximum percentage of monthly income
            allowed to go toward all loan obligations combined.
            Defaults to 50.0.

    Returns:
        A dict indicating whether the customer is likely eligible,
        along with the maximum affordable EMI and maximum loan amount
        at the given rate and tenure.
    """
    max_total_emi = monthly_income * (max_foir_percent / 100)
    max_new_emi = max_total_emi - existing_monthly_emis

    if max_new_emi <= 0:
        return {
            "is_eligible": False,
            "max_affordable_emi": 0.0,
            "max_loan_amount": 0.0,
            "reason": (
                "Existing EMI obligations already exceed the maximum " "allowed FOIR."
            ),
        }

    monthly_rate = (annual_interest_rate_percent / 100) / 12
    growth_factor = (1 + monthly_rate) ** tenure_months
    max_loan_amount = max_new_emi * (growth_factor - 1) / (monthly_rate * growth_factor)

    return {
        "is_eligible": True,
        "max_affordable_emi": round(max_new_emi, 2),
        "max_loan_amount": round(max_loan_amount, 2),
        "max_foir_percent": max_foir_percent,
    }
