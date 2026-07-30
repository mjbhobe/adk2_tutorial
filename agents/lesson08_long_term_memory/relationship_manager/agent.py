"""Lesson 8: Long-Term Memory.

A relationship manager assistant for a wealth management desk. It
saves every turn to long-term memory automatically via an
after_agent_callback, and searches that memory before answering
investment questions so it can recall client preferences stated in
previous, entirely separate sessions.
"""

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import load_memory

from common.model_config import get_model


async def save_to_memory(callback_context: CallbackContext) -> None:
    """Saves this turn to long-term memory after every agent response.

    Fires automatically after every turn via after_agent_callback.
    Requires a memory_service to be wired into the Runner in main.py;
    without one, this raises a ValueError at runtime.

    Args:
        callback_context: Injected automatically by ADK. Must be named
            exactly "callback_context" — ADK enforces this.
    """
    await callback_context.add_session_to_memory()


AGENT_INSTRUCTION = (
    "You are a relationship manager assistant for a private wealth "
    "management desk. Before answering any investment-related question, "
    "use the load_memory tool to check whether this client has stated "
    "relevant preferences in past conversations, such as risk tolerance, "
    "sector interests, or exclusions like fossil fuels or tobacco. "
    "If memory returns relevant context, use it to personalise your "
    "response without asking the client to repeat themselves. If memory "
    "returns nothing relevant, answer using only what the client has "
    "said in this conversation. Never fabricate preferences the client "
    "did not state. Always clarify you are providing general information, "
    "not personalised investment advice, which requires a licensed advisor."
)

root_agent = Agent(
    name="relationship_manager_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description=(
        "Wealth management RM assistant that recalls client preferences "
        "across separate conversations using long-term memory."
    ),
    tools=[load_memory],
    after_agent_callback=save_to_memory,
)

