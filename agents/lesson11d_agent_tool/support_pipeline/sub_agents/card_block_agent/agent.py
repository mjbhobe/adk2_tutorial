"""Lesson 11d: Card block agent, the other specialist behind the router.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import block_card

instruction = """Extract the card_number and the reason (lost or
stolen) from the request and call `block_card` with them. Confirm the
block back in one sentence.
"""

card_block_agent = Agent(
    name="card_block_agent",
    model=get_model("primary"),
    description="Blocks a customer's lost or stolen card.",
    instruction=instruction,
    tools=[block_card],
)
