"""Lesson 11d: Customer support agent, routes between two specialists at runtime.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from common.model_config import get_model

from .sub_agents.balance_inquiry_agent.agent import balance_inquiry_agent
from .sub_agents.card_block_agent.agent import card_block_agent

instruction = """You handle customer banking requests.

If the customer wants to know their balance, use the balance inquiry
tool. If the customer reports a lost or stolen card, use the card
block tool. Use whichever one actually applies to what they asked,
not both.
"""

root_agent = Agent(
    name="customer_support_agent",
    model=get_model("primary"),
    description="Routes customer banking requests to the right specialist.",
    instruction=instruction,
    tools=[
        AgentTool(agent=balance_inquiry_agent),
        AgentTool(agent=card_block_agent),
    ],
)
