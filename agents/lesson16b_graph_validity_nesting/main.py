"""
Lesson 16b: driver for the nested loan disbursement workflow

Runs the outer workflow for two loan amounts, one that clears
automatically and one that trips manual review, exercising the
nested compliance_check_workflow both ways.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import asyncio
import json

from google.adk.runners import InMemoryRunner

from workflow import loan_disbursement_workflow


async def run_loan(runner: InMemoryRunner, session_id: str, loan_amount: float) -> None:
    """Seeds session state, runs the graph once, and prints the result.

    Args:
        runner: The shared InMemoryRunner wrapping the workflow.
        session_id: A unique session id for this run.
        loan_amount: The loan principal to test with.
    """
    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id="lesson16b_user",
        session_id=session_id,
        state={"manual_review_limit": 1_000_000},
    )

    payload = json.dumps(
        {"loan_amount": loan_amount, "fee_percentage": 2.0, "gst_rate": 18.0}
    )

    events = await runner.run_debug(
        payload, quiet=True, session_id=session_id, user_id="lesson16b_user"
    )

    print(f"loan_amount={loan_amount} -> {events[-1].output}\n")


async def main() -> None:
    """Runs the graph for two different loan amounts."""
    runner = InMemoryRunner(agent=loan_disbursement_workflow)

    print("Run 1: a loan that clears automatically")
    await run_loan(runner, session_id="run_1", loan_amount=50_000)

    print("Run 2: a loan that trips manual review")
    await run_loan(runner, session_id="run_2", loan_amount=5_000_000)


if __name__ == "__main__":
    asyncio.run(main())
