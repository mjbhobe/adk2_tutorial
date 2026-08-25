"""Lesson 16a: LLM Nodes.

Picks up the loan disbursement graph from Lesson 16 and extends it
with an Agent node. Everything through `log_decision` is unchanged.
Two new nodes follow it: `draft_notification`, an `Agent` running in
single_turn mode that writes the customer-facing message, and
`dispatch_notification`, a plain function node that receives that
message and finalizes the result.

The loan numbers are synthetic, same as Lesson 16. The notification
text is not scripted, it is genuine model output, so the exact
wording will differ between runs. That is expected, not a bug.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from google.adk.agents import Agent
from google.adk.workflow import START, Workflow, node

from common.model_config import get_model


@node
async def calculate_deductions(ctx: Any, node_input: str) -> dict:
    """Parses the incoming loan request and works out fee plus tax.

    Unchanged from Lesson 16.
    """
    params = json.loads(node_input)
    loan_amount = params["loan_amount"]
    fee_percentage = params["fee_percentage"]
    gst_rate = params["gst_rate"]

    base_fee = loan_amount * (fee_percentage / 100)
    tax = base_fee * (gst_rate / 100)
    total_deductions = base_fee + tax

    print(
        f"  [calculate_deductions] base_fee={base_fee}, tax={tax}, "
        f"total_deductions={total_deductions}"
    )
    return {"loan_amount": loan_amount, "total_deductions": total_deductions}


@node
async def calculate_net_payout(ctx: Any, node_input: dict) -> dict:
    """Works out what the borrower actually receives.

    Unchanged from Lesson 16.
    """
    loan_amount = node_input["loan_amount"]
    total_deductions = node_input["total_deductions"]
    net_disbursement = loan_amount - total_deductions

    result = {"net_disbursement": net_disbursement, "status": "READY_FOR_TRANSFER"}
    print(f"  [calculate_net_payout] {result}")
    return result


@node
async def check_compliance_threshold(
    ctx: Any, node_input: dict, manual_review_limit: float
) -> dict:
    """Decides whether this payout needs a human to sign off on it.

    Unchanged from Lesson 16.
    """
    net_disbursement = node_input["net_disbursement"]
    print(
        f"  [check_compliance_threshold] net_disbursement={net_disbursement}, "
        f"manual_review_limit={manual_review_limit}"
    )

    if net_disbursement > manual_review_limit:
        ctx.route = "needs_review"
    else:
        ctx.route = "auto_clear"

    return node_input


@node
async def flag_for_review(node_input: dict) -> dict:
    """Marks a payout as held for manual compliance review.

    Unchanged from Lesson 16.
    """
    node_input["status"] = "PENDING_MANUAL_REVIEW"
    return node_input


@node
async def auto_disburse(node_input: dict) -> dict:
    """Marks a payout as cleared for automatic disbursement.

    Unchanged from Lesson 16.
    """
    node_input["status"] = "AUTO_DISBURSED"
    return node_input


@node
async def log_decision(node_input: dict) -> dict:
    """The point both branches converge on.

    Unchanged from Lesson 16, except it is no longer the last node in
    the graph. Its output now becomes `node_input` for
    `draft_notification` below.
    """
    print(f"  [log_decision] final decision: {node_input}")
    return node_input


class NotificationMessage(BaseModel):
    """The structured shape `draft_notification` must return.

    A plain Pydantic model, the same kind Lesson 5 used for structured
    output. What is new here is not the schema itself, it is that this
    schema is doing two jobs at once: it shapes what the model is
    asked to produce, and it validates the node's output for the
    graph. One field, `output_schema`, both jobs.
    """

    subject: str
    body: str


_draft_notification_instruction = """You are a loan operations assistant.
You will receive a JSON object describing a loan decision, with keys
`net_disbursement` and `status`. `status` is either `AUTO_DISBURSED` or
`PENDING_MANUAL_REVIEW`.

Write a short customer-facing notification about this decision. Keep
the tone plain and reassuring, no jargon. If the status is
`AUTO_DISBURSED`, confirm the amount and that funds are on the way.
If it is `PENDING_MANUAL_REVIEW`, explain that the loan needs a quick
compliance check before funds move, without alarming the customer.
"""

draft_notification = Agent(
    name="draft_notification",
    model=get_model("primary"),
    description="Drafts a structured customer notification for a loan decision.",
    instruction=_draft_notification_instruction,
    output_schema=NotificationMessage,
)
# No `mode=` set here on purpose. A standalone Agent used directly as
# a workflow node, with no parent agent, defaults to `mode='single_turn'`.
# single_turn means one exchange: the node receives `node_input`, the
# model replies once, and that reply becomes the node's output.


@node
async def dispatch_notification(node_input: dict) -> dict:
    """Receives the drafted notification and finalizes the result.

    `node_input` here is the dict `draft_notification` returned,
    already validated against `NotificationMessage`. In a real system
    this is where you would actually send the email or SMS. Here it
    just prints and returns the combined result.

    Args:
        node_input: `{"subject": ..., "body": ...}`, the validated
            output of `draft_notification`.

    Returns:
        The same dict, unchanged. This is the graph's terminal node.
    """
    print(f"  [dispatch_notification] subject: {node_input['subject']}")
    print(f"  [dispatch_notification] body: {node_input['body']}")
    return node_input


loan_disbursement_workflow = Workflow(
    name="loan_disbursement_workflow",
    edges=[
        (START, calculate_deductions, calculate_net_payout, check_compliance_threshold),
        (check_compliance_threshold, {"needs_review": flag_for_review, "auto_clear": auto_disburse}),
        (flag_for_review, log_decision),
        (auto_disburse, log_decision),
        (log_decision, draft_notification, dispatch_notification),
    ],
)

root_agent = loan_disbursement_workflow
