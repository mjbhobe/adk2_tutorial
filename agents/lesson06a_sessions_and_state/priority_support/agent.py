"""Lesson 6a: Sessions & State.

A priority banking support assistant whose session arrives pre-seeded
with CRM context, customer name, account tier, and relationship
manager, before the agent ever sees a single message. The agent reads
that context straight from its instruction.
"""

from google.adk.agents import Agent

from common.model_config import get_model

AGENT_INSTRUCTION = (
    "You are a priority banking support assistant. You are speaking "
    "with {customer_name}, a {account_tier} tier customer whose "
    "relationship manager is {relationship_manager_name}. Greet them "
    "by name. Platinum and Gold tier customers should be offered a "
    "direct handoff to their relationship manager for anything beyond "
    "a simple question; Standard tier customers can be helped "
    "directly for routine issues."
)

root_agent = Agent(
    name="priority_support_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description=(
        "Priority banking support assistant aware of customer tier and "
        "relationship manager, pre-seeded from CRM data."
    ),
)