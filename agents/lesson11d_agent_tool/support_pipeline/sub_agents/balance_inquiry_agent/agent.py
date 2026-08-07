"""Lesson 11d: Balance inquiry agent, one of two specialists behind the router.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import get_account_balance

instruction = """Extract the account_number from the request and call
`get_account_balance` with it. Report the balance back in one sentence.
"""

balance_inquiry_agent = Agent(
    name="balance_inquiry_agent",
    model=get_model("primary"),
    description="Looks up a customer's current account balance.",
    instruction=instruction,
    tools=[get_account_balance],
)
