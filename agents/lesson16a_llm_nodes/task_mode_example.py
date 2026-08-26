"""
Lesson 16a: standalone task-mode example

A small, self-contained example separate from the loan disbursement
workflow. Shows a task-mode agent calling a tool across two rounds
before signaling completion through finish_task.

Needs a real, working model configured in common/model_config.py to
actually run.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import asyncio

from google.adk.workflow import START, Workflow
from google.adk.runners import InMemoryRunner

from grace_period.agent import grace_period_agent

grace_period_workflow = Workflow(
    name="grace_period_workflow",
    edges=[(START, grace_period_agent)],
)


async def main() -> None:
    """Runs the grace-period task-mode agent once and prints the result."""
    runner = InMemoryRunner(agent=grace_period_workflow)
    events = await runner.run_debug("PENDING_MANUAL_REVIEW", quiet=True)
    print("Final result:", events[-1].output)


if __name__ == "__main__":
    asyncio.run(main())
