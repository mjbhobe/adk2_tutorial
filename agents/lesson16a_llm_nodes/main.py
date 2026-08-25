"""Driver for Lesson 16a: LLM Nodes.

Runs the extended loan disbursement graph. Same structure as Lesson
16's main.py: state seeded before each run, `InMemoryRunner.run_debug`
plus `events[-1].output` for the result, `run_agent_query` still
skipped for the same reason as Lesson 16, part of this graph is
still pure function nodes, and even for the Agent node, `run_debug`
already surfaces its output directly.

This needs a real, working model configured in `common/model_config.py`
to actually run. The loan numbers are deterministic. The notification
text is not, it is genuine model output, so do not expect the exact
wording shown in the lesson.
"""

from __future__ import annotations

import asyncio
import json

from google.adk.runners import InMemoryRunner

from agent import loan_disbursement_workflow


async def run_loan(runner: InMemoryRunner, session_id: str, loan_amount: float) -> None:
    """Seeds session state, runs the graph once, and prints the result."""
    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id="lesson16a_user",
        session_id=session_id,
        state={"manual_review_limit": 1_000_000},
    )

    payload = json.dumps(
        {"loan_amount": loan_amount, "fee_percentage": 2.0, "gst_rate": 18.0}
    )

    events = await runner.run_debug(
        payload, quiet=True, session_id=session_id, user_id="lesson16a_user"
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
