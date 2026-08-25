"""Lesson 16, Stage 2: adding a conditional branch.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import asyncio
import json

from google.adk.workflow import START, Workflow, node
from google.adk.runners import InMemoryRunner


@node
async def calculate_deductions(ctx, node_input: str) -> dict:
    print("  [calculate_deductions] node running")
    print(f"      Got input: {node_input}")
    params = json.loads(node_input)
    loan_amount = params["loan_amount"]
    fee_percentage = params["fee_percentage"]
    gst_rate = params["gst_rate"]

    base_fee = loan_amount * (fee_percentage / 100)
    tax = base_fee * (gst_rate / 100)
    total_deductions = base_fee + tax

    resp = {"loan_amount": loan_amount, "total_deductions": total_deductions}
    print(f"        Returning: {resp}")
    return resp


@node
async def calculate_net_payout(ctx, node_input: dict) -> dict:
    print("  [calculate_net_payout] node running")
    print(f"      Got input: {node_input}")
    loan_amount = node_input["loan_amount"]
    total_deductions = node_input["total_deductions"]
    net_disbursement = loan_amount - total_deductions

    resp = {"net_disbursement": net_disbursement, "status": "READY_FOR_TRANSFER"}
    print(f"        Returning: {resp}")
    return resp


@node
async def check_compliance_threshold(
    ctx, node_input: dict, manual_review_limit: float
) -> dict:
    print("  [check_compliance_threshold] node running")
    net_disbursement = node_input["net_disbursement"]
    print(
        f"      Got input: {node_input} - manual_review_limit: {manual_review_limit} - net_disbursement: {net_disbursement}"
    )

    if net_disbursement > manual_review_limit:
        print("      Net disbursement > manual review limit, routing to 'needs_review'")
        ctx.route = "needs_review"
    else:
        print("      Net disbursement <= manual review limit, routing to 'auto_clear'")
        ctx.route = "auto_clear"

    print(f"        Returning: {node_input}")
    return node_input


@node
async def flag_for_review(node_input: dict) -> dict:
    print("  [flag_for_review] node running")
    node_input["status"] = "PENDING_MANUAL_REVIEW"
    return node_input


@node
async def auto_disburse(node_input: dict) -> dict:
    print("  [auto_disburse] node running")
    node_input["status"] = "AUTO_DISBURSED"
    return node_input


@node
async def log_decision(node_input: dict) -> dict:
    print("  [log_decision] node running")
    return node_input


loan_disbursement_workflow = Workflow(
    name="loan_disbursement_workflow",
    edges=[
        (START, calculate_deductions, calculate_net_payout, check_compliance_threshold),
        (
            check_compliance_threshold,
            {"needs_review": flag_for_review, "auto_clear": auto_disburse},
        ),
        (flag_for_review, log_decision),
        (auto_disburse, log_decision),
    ],
)


async def run_loan(runner: InMemoryRunner, session_id: str, loan_amount: float) -> None:
    # first create a session because we need to seed the context with
    # manual review limit for the compliance check node
    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id="lesson16_user",
        session_id=session_id,
        state={"manual_review_limit": 1_000_000},
    )
    payload = json.dumps(
        {"loan_amount": loan_amount, "fee_percentage": 2.0, "gst_rate": 18.0}
    )
    events = await runner.run_debug(
        payload,
        quiet=True,
        session_id=session_id,
        user_id="lesson16_user",
    )
    print(f"Final result for loan_amount={loan_amount}:", events[-1].output)


async def main() -> None:
    runner = InMemoryRunner(agent=loan_disbursement_workflow)

    print("Run 1: a loan that clears automatically")
    await run_loan(runner, session_id="run_1", loan_amount=50_000)

    print("\nRun 2: a loan that trips manual review")
    await run_loan(runner, session_id="run_2", loan_amount=5_000_000)


if __name__ == "__main__":
    asyncio.run(main())
