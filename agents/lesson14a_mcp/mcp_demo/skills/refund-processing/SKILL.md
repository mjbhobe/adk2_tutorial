---
name: refund-processing
description: |
  Issues a refund for a Stripe charge or payment intent. Use this only
  when a customer request clearly warrants a refund, never issue one
  speculatively or without a stated reason.
metadata:
  adk_additional_tools:
    - create_refund
---

# Refund Processing

Refunds are irreversible once processed. Before calling `create_refund`:

1. Confirm you have the charge ID or payment intent ID to refund, not
   just a customer name or email, ask for it if it's missing.
2. Confirm the reason for the refund is stated, duplicate charge,
   fraudulent, or requested by customer.
3. Call `create_refund` with the charge or payment intent ID.
4. Report the refund ID and status back plainly, don't editorialize.

Never call `create_refund` speculatively "just in case." If the request
is ambiguous, ask for clarification instead of guessing.
