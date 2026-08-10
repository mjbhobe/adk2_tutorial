"""Lesson 13a: Risk specialist agent, wrapped as an AgentTool.

A judgment task, not a quick lookup, worth its own dedicated agent
turn rather than a skill an orchestrator loads for a few seconds.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import calculate_risk_score

instruction = """You are a loan risk specialist. Given an applicant's
credit_score, annual_income, loan_amount, tenure_months, and
has_defaults, call `calculate_risk_score` with those five values and
report the risk_score, risk_band, and emi_to_income_ratio back.

Always call the tool. Never estimate the score yourself.
"""

risk_specialist_agent = Agent(
    name="risk_specialist_agent",
    model=get_model("primary"),
    description="Assesses loan risk given credit and applicant details, and returns a risk score and band.",
    instruction=instruction,
    tools=[calculate_risk_score],
)
