"""
Lesson 16a: the grace_period agent

Defines the structured output schema and the task-mode Agent that
decides whether a loan qualifies for a grace period.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from pydantic import BaseModel

from google.adk.agents import Agent

from common.model_config import get_model
from .tools import lookup_grace_period


class GracePeriodDecision(BaseModel):
    """The structured shape grace_period_agent must finish with.

    Attributes:
        eligible: Whether the loan qualifies for a grace period.
        extension_days: The number of days granted, 0 if not eligible.
    """

    eligible: bool
    extension_days: int


_INSTRUCTION = """You are a loan operations assistant.
You will receive a loan's status. Call `lookup_grace_period` with that
status to check eligibility, then decide the final extension in days.
Call `finish_task` once you have decided, do not just describe your
answer in text.
"""

grace_period_agent = Agent(
    name="grace_period_agent",
    model=get_model("primary"),
    description="Decides whether a loan qualifies for a grace period.",
    instruction=_INSTRUCTION,
    tools=[lookup_grace_period],
    mode="task",
    output_schema=GracePeriodDecision,
)
# mode has to be set explicitly here. Unlike a standalone Agent node,
# which defaults to single_turn, task mode is never assumed for you.
