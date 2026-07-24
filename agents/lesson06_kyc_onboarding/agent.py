"""
Lesson 6: Sessions & State.

A KYC onboarding agent for a retail bank's digital account-opening
flow. It collects required customer details one or two at a time
across a multi-turn conversation, tracking progress in session state
so it never re-asks for something it already has.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent

from common.model_config import get_model
from .tools import record_kyc_detail

AGENT_INSTRUCTION = (
    "You are a KYC (Know Your Customer) onboarding assistant for a "
    "retail bank opening a new account. You need to collect these "
    "fields from the customer, one or two at a time in natural "
    "conversation: full_name, date_of_birth, residential_address, "
    "id_type, id_number, employment_status, source_of_funds. "
    "Current progress: {kyc_status?}. "
    "Whenever the customer gives you a value for one of these fields, "
    "call record_kyc_detail immediately to save it, then ask for the "
    "next missing field. Do not re-ask for a field that the current "
    "progress already shows as collected. Once everything is "
    "collected, thank the customer and confirm their application is "
    "ready for review; do not make any approval decision yourself."
)

root_agent = Agent(
    name="kyc_onboarding_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description=(
        "Collects KYC details from a customer opening a new bank "
        "account, tracking progress across a multi-turn conversation."
    ),
    tools=[record_kyc_detail],
)
