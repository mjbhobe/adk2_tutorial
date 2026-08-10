#!/usr/bin/env python3
"""Lesson 13a: EMI calculator, run directly by the emi-calculator skill.

This runs as a real subprocess when run_skill_script executes it, not
as a Python function called in-process, so it takes plain command-line
arguments and prints its result to stdout, exactly like any standalone
CLI script would.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import argparse
import json


def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Calculates the standard amortized EMI for a loan.

    Same reducing-balance formula used throughout this series.

    Args:
        principal: Loan amount, in INR.
        annual_rate: Annual interest rate, as a percentage.
        tenure_months: Loan tenure, in months.

    Returns:
        The monthly EMI, in INR.
    """
    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        return principal / tenure_months
    growth_factor = (1 + monthly_rate) ** tenure_months
    return principal * monthly_rate * growth_factor / (growth_factor - 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate a loan's exact monthly EMI.")
    parser.add_argument("--principal", type=float, required=True, help="Loan amount, in INR")
    parser.add_argument("--annual-rate", type=float, required=True, help="Annual interest rate, as a percentage")
    parser.add_argument("--tenure-months", type=int, required=True, help="Loan tenure, in months")
    args = parser.parse_args()

    emi = calculate_emi(args.principal, args.annual_rate, args.tenure_months)

    print(json.dumps({
        "principal": args.principal,
        "annual_rate": args.annual_rate,
        "tenure_months": args.tenure_months,
        "emi": round(emi, 2),
    }))


if __name__ == "__main__":
    main()
