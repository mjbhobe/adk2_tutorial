"""Lesson 16a: a small, standalone task-mode example.

single_turn is one exchange: the model replies once and the node is
done. task mode is different. A task-mode agent can call tools across
several rounds, deciding for itself how many rounds it needs, and
only finishes when it explicitly says it is done. That "I am done"
signal is a real mechanism, not a convention: ADK attaches a tool
called `finish_task` to every task-mode agent automatically. The model
calls it when ready, passing its final answer as the tool's arguments,
shaped by the agent's `output_schema`. Whatever it passes becomes the
node's output.

This example is deliberately separate from the loan disbursement
graph. It decides whether a loan in manual review qualifies for a
short grace period, calling one tool to check eligibility before
deciding.
"""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from google.adk.agents import Agent
from google.adk.workflow import START, Workflow
from google.adk.runners import InMemoryRunner

from common.model_config import get_model


def lookup_grace_period(loan_status: str) -> dict:
    """Looks up whether a loan in this status can get a grace period.

    A plain function tool, the same kind Lesson 3 covered. Nothing
    about tool-calling itself is new here, what is new is that this
    tool is being called by an agent running as a graph node.

    Args:
        loan_status: The loan's current status, e.g.
            "PENDING_MANUAL_REVIEW".

    Returns:
        A dict with `eligible` and `max_days`. Deterministic and
        synthetic, not a real policy lookup.
    """
    if loan_status == "PENDING_MANUAL_REVIEW":
        return {"eligible": True, "max_days": 15}
    return {"eligible": False, "max_days": 0}


class GracePeriodDecision(BaseModel):
    """The structured shape the task agent must finish with."""

    eligible: bool
    extension_days: int


_grace_period_instruction = """You are a loan operations assistant.
You will receive a loan's status. Call `lookup_grace_period` with that
status to check eligibility, then decide the final extension in days.
Call `finish_task` once you have decided, do not just describe your
answer in text.
"""

grace_period_agent = Agent(
    name="grace_period_agent",
    model=get_model("primary"),
    description="Decides whether a loan qualifies for a grace period.",
    instruction=_grace_period_instruction,
    tools=[lookup_grace_period],
    mode="task",
    output_schema=GracePeriodDecision,
)
# mode has to be set explicitly here. Unlike a standalone Agent node,
# which defaults to single_turn, task mode is never assumed for you.

grace_period_workflow = Workflow(
    name="grace_period_workflow",
    edges=[(START, grace_period_agent)],
)


async def main() -> None:
    runner = InMemoryRunner(agent=grace_period_workflow)
    events = await runner.run_debug("PENDING_MANUAL_REVIEW", quiet=True)
    print("Final result:", events[-1].output)


if __name__ == "__main__":
    asyncio.run(main())
