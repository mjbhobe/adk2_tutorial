"""
Lesson 16b: max_concurrency example

Three independent checks on a new loan application, fanned out to run
at once, then converged. Runs the same graph twice, once unlimited
and once capped at max_concurrency=1, so the timing difference is
visible directly.

Every check here just sleeps to stand in for a slow external lookup,
credit bureau, fraud database, income verification service. None of
it is real, the timing behavior is what matters.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import asyncio
import json
import time

from google.adk.workflow import START, Workflow, node, JoinNode
from google.adk.runners import InMemoryRunner


@node
async def intake(ctx, node_input: str) -> dict:
    """Parses the incoming loan application.

    Args:
        ctx: The node's execution context. Unused here.
        node_input: A JSON string with the applicant id.

    Returns:
        The parsed application dict.
    """
    return json.loads(node_input)


@node
async def credit_check(node_input: dict) -> dict:
    """Simulates a credit bureau lookup.

    Args:
        node_input: The application dict.

    Returns:
        A dict with a synthetic credit_score.
    """
    print("  [credit_check] started")
    await asyncio.sleep(0.5)
    print("  [credit_check] finished")
    return {"credit_score": 720}


@node
async def fraud_check(node_input: dict) -> dict:
    """Simulates a fraud database lookup.

    Args:
        node_input: The application dict.

    Returns:
        A dict with a synthetic fraud_flag.
    """
    print("  [fraud_check] started")
    await asyncio.sleep(0.5)
    print("  [fraud_check] finished")
    return {"fraud_flag": False}


@node
async def income_check(node_input: dict) -> dict:
    """Simulates an income verification lookup.

    Args:
        node_input: The application dict.

    Returns:
        A dict with a synthetic income_verified flag.
    """
    print("  [income_check] started")
    await asyncio.sleep(0.5)
    print("  [income_check] finished")
    return {"income_verified": True}


join_checks = JoinNode(name="join_checks")


def build_intake_workflow(max_concurrency: int | None = None) -> Workflow:
    """Builds the intake workflow, optionally capping parallel nodes.

    Args:
        max_concurrency: Maximum number of graph-scheduled nodes
            allowed to run at once. None means unlimited.

    Returns:
        A fresh Workflow instance.
    """
    return Workflow(
        name="intake_workflow",
        edges=[(START, intake, (credit_check, fraud_check, income_check), join_checks)],
        max_concurrency=max_concurrency,
    )


async def run(workflow: Workflow, label: str) -> None:
    """Runs the given workflow once and prints the elapsed time.

    Args:
        workflow: The Workflow to run.
        label: A short label identifying this run in the printed output.
    """
    runner = InMemoryRunner(agent=workflow)
    start = time.time()
    events = await runner.run_debug('{"applicant_id": "A123"}', quiet=True)
    elapsed = time.time() - start
    print(f"{label}: {elapsed:.2f}s total -> {events[-1].output}\n")


async def main() -> None:
    """Runs the intake workflow unlimited, then capped at 1."""
    await run(build_intake_workflow(), "No max_concurrency (default, unlimited)")
    await run(build_intake_workflow(max_concurrency=1), "max_concurrency=1")


if __name__ == "__main__":
    asyncio.run(main())
