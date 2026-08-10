---
name: emi-calculator
description: |
  Calculates the exact monthly EMI (equated monthly installment) for a
  loan, given the principal, annual interest rate, and tenure in
  months. Use this whenever a precise EMI figure is needed rather than
  an estimate.
---

# EMI Calculator

Never estimate an EMI yourself, run the calculator script instead.

Call `run_skill_script` with:
- `skill_name`: "emi-calculator"
- `file_path`: "scripts/calculate_emi.py"
- `args`: an object with `principal`, `annual-rate`, and `tenure-months`,
  matching the loan's amount (INR), annual interest rate (percentage),
  and tenure (months)

For example, for a loan of 500000 at 10.5% over 36 months:
`args={"principal": "500000", "annual-rate": "10.5", "tenure-months": "36"}`

The script prints a JSON object to stdout with the calculated `emi`.
Read the EMI from that output, don't recompute it yourself.
