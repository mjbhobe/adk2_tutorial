"""Lesson 16, Stage 1: a plain linear chain.

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


sequential_flow = Workflow(
    name="sequential_flow",
    edges=[(START, calculate_deductions, calculate_net_payout)],
)


async def main() -> None:
    runner = InMemoryRunner(agent=sequential_flow)
    # NOTE: you can always accept these parameters as inputs
    # from the user, build the JSON string & call the workfow
    # Try that as an exercise.
    events = await runner.run_debug(
        '{"loan_amount": 50000, "fee_percentage": 2.0, "gst_rate": 18.0}',
        quiet=True,
    )
    print("Final result:", events[-1].output)


if __name__ == "__main__":
    asyncio.run(main())
