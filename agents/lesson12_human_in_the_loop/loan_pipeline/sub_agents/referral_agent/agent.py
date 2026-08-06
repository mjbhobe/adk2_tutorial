"""Lesson 12: Referral agent, writes up a follow-up task for a referred case.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import create_referral_task

instruction = """You are the referral agent for a loan approval pipeline
at a retail bank.

Session state has:

Officer decision: {officer_decision?}
Credit result: {credit_result}
Risk result: {risk_result}

If officer_decision is exactly "REFER", call `create_referral_task`
with the applicant's name, the risk_band from the risk result, and a
short reason drawn from what the credit and risk results actually show,
for example a high loan amount relative to income, or a middling risk
score. Then briefly confirm the task was created.

If officer_decision is anything else, "APPROVE", "REJECT", or missing,
do not call the tool. Just note in one sentence that referral doesn't
apply to this application.
"""

referral_agent = Agent(
    name="referral_agent",
    model=get_model("primary"),
    description="Creates a follow-up task for a senior underwriter if the officer referred the application.",
    instruction=instruction,
    tools=[create_referral_task],
)
