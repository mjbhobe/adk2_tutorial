"""Lesson 6c: Artifacts — loan documentation agent."""

from google.adk.agents import Agent

from common.model_config import get_model
from .tools import calculate_loan_summary

AGENT_INSTRUCTION = (
    "You are a loan documentation assistant for a retail bank. "
    "When a customer provides their loan details, use the "
    "calculate_loan_summary tool to compute the figures and generate "
    "a PDF summary report. After the tool runs, confirm the monthly EMI "
    "and total repayment to the customer, and let them know their "
    "summary report has been saved as a PDF document they can download."
)

root_agent = Agent(
    name="loan_report_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description="Calculates loan figures and generates a PDF summary as an artifact.",
    tools=[calculate_loan_summary],
)
