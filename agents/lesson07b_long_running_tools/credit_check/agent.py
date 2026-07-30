"""Lesson 7b: Long-Running Tools — loan processing agent."""

from google.adk.agents import Agent

from common.model_config import get_model
from .tools import credit_bureau_check

AGENT_INSTRUCTION = (
    "You are a loan processing assistant for a retail bank. When asked "
    "to run a credit check on an applicant, use the credit bureau check "
    "tool and inform the customer that this will take a moment. Once "
    "the result is back, summarise the credit score, credit band, and "
    "whether the requested loan amount is within the recommended limit. "
    "Never guess or estimate credit scores; only report what the tool "
    "returns."
)

root_agent = Agent(
    name="credit_check_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description="Runs credit bureau checks for loan applicants.",
    tools=[credit_bureau_check],
)
