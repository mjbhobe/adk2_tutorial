"""
Lesson 16b: nested loan disbursement workflow

The compliance-check portion of the loan disbursement graph, pulled
out into its own Workflow, and reused as a single node inside the
outer graph.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import json
from typing import Any

from google.adk.workflow import START, Workflow, node


@node
async def calculate_deductions(ctx: Any, node_input: str) -> dict:
    """Parses the incoming loan request and works out fee plus tax.

    Args:
        ctx: The node's execution context. Unused here.
        node_input: A JSON string with loan_amount, fee_percentage,
            and gst_rate.

    Returns:
        A dict with loan_amount and total_deductions.
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

    Args:
        ctx: The node's execution context. Unused here.
        node_input: The dict returned by calculate_deductions.

    Returns:
        A dict with net_disbursement and a starting status.
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

    Args:
        ctx: The node's execution context. Used to set ctx.route.
        node_input: The dict returned by calculate_net_payout.
        manual_review_limit: Read from ctx.state["manual_review_limit"].

    Returns:
        The same dict it received, unchanged.
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

    Args:
        node_input: The dict carried over from check_compliance_threshold.

    Returns:
        The same dict with status updated.
    """
    node_input["status"] = "PENDING_MANUAL_REVIEW"
    return node_input


@node
async def auto_disburse(node_input: dict) -> dict:
    """Marks a payout as cleared for automatic disbursement.

    Args:
        node_input: The dict carried over from check_compliance_threshold.

    Returns:
        The same dict with status updated.
    """
    node_input["status"] = "AUTO_DISBURSED"
    return node_input


@node
async def log_decision(node_input: dict) -> dict:
    """The point both branches converge on, and the inner workflow's
    own terminal node.

    Args:
        node_input: The dict from either branch.

    Returns:
        The same dict, unchanged. Becomes the inner workflow's output,
        which becomes node_input for whatever follows it in the outer
        graph.
    """
    print(f"  [log_decision] final decision: {node_input}")
    return node_input


compliance_check_workflow = Workflow(
    name="compliance_check_workflow",
    edges=[
        (START, check_compliance_threshold, {"needs_review": flag_for_review, "auto_clear": auto_disburse}),
        (flag_for_review, log_decision),
        (auto_disburse, log_decision),
    ],
)

loan_disbursement_workflow = Workflow(
    name="loan_disbursement_workflow",
    edges=[(START, calculate_deductions, calculate_net_payout, compliance_check_workflow)],
)

root_agent = loan_disbursement_workflow
