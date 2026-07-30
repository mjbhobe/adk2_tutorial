"""Lesson 7a: Callbacks in Practice.

Agent definition for the wealth management advisory agent. This file
declares what the agent IS: its model, instruction, tools, and which
callback functions are registered at each interception point. The
callback implementations live in callbacks.py.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent

from common.model_config import get_model
from .tools import get_portfolio_summary, get_market_indices
from .callbacks import (
    check_customer_tier,
    inject_market_context,
    scan_for_unsupported_advice,
    log_tool_invocation,
    validate_tool_result,
    save_to_memory,
)

AGENT_INSTRUCTION = (
    "You are a wealth management advisor for a private bank. You are "
    "speaking with {customer_name}, a {account_tier} tier customer. "
    "You can look up their portfolio summary and current market index "
    "levels. You can discuss their portfolio allocation, explain market "
    "movements, and answer general investment questions. You cannot make "
    "specific buy or sell recommendations; for those, direct the customer "
    "to their relationship manager. This is turn {turn_count?} of the "
    "current conversation."
)

root_agent = Agent(
    name="wealth_advisor_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description=(
        "Wealth management advisory agent with compliance guardrails, "
        "audit logging, and long-term memory across sessions."
    ),
    tools=[get_portfolio_summary, get_market_indices],
    before_agent_callback=check_customer_tier,
    before_model_callback=inject_market_context,
    after_model_callback=scan_for_unsupported_advice,
    before_tool_callback=log_tool_invocation,
    after_tool_callback=validate_tool_result,
    after_agent_callback=save_to_memory,
)
