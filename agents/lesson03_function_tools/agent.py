"""Lesson 3: Function Tools.

A loan desk assistant for a retail bank that calculates EMIs (Equated
Monthly Installments) and checks loan affordability against a
customer's income, using two real Python functions as ADK tools
rather than asking the model to do the arithmetic itself.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent

from common.model_config import get_model
from .tools import calculate_emi, check_loan_affordability

AGENT_INSTRUCTION = (
    "You are a loan desk assistant for a retail bank. Customers will "
    "ask you about monthly payments on a loan they're considering, or "
    "whether they can afford a certain loan amount. Use the "
    "calculate_emi tool for the first kind of question, and the "
    "check_loan_affordability tool for the second. Always state the "
    "key numbers clearly: EMI, total interest, or maximum loan amount "
    "as applicable. If the customer hasn't given you enough "
    "information to call a tool, such as a missing interest rate or "
    "tenure, ask for it before calculating anything. Never estimate "
    "or guess a number yourself; only report numbers that came from a "
    "tool call."
)

root_agent = Agent(
    name="loan_calculator_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description=(
        "Calculates loan EMIs and checks loan affordability against "
        "customer income for a retail bank's loan desk."
    ),
    tools=[calculate_emi, check_loan_affordability],
)
