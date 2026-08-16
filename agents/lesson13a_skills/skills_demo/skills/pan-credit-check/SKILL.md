---
name: pan-credit-check
description: |
  Validates an Indian PAN (Permanent Account Number) and fetches a mock
  credit bureau report for that PAN. Use this whenever an agent needs
  to check a PAN's format or look up an applicant's credit history.
metadata:
  adk_additional_tools:
    - validate_pan_format
    - get_credit_bureau_report
---

# PAN & Credit Check

A PAN (Permanent Account Number) is India's tax ID, and the standard
identity check for a financial application. A valid PAN is exactly 10
characters: 5 uppercase letters, 4 digits, 1 uppercase letter, for
example ABCDE1234F.

When you need to check or use a PAN:

1. Call `validate_pan_format` with the PAN as given. Never judge the
   format yourself, always call the tool.
2. If it's valid, and you also need the applicant's credit history,
   call `get_credit_bureau_report` with the same PAN.
3. If the format check fails, tell the caller the PAN is invalid and
   why, don't attempt a credit check on an invalid PAN.

Both tools return deterministic mock data for this lesson, the same
result every time for a given PAN, standing in for a real government
PAN registry and a real credit bureau.
