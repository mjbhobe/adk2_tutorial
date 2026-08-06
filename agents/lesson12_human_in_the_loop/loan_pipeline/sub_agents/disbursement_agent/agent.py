"""Lesson 12: Disbursement agent, generates the loan offer letter.

Always runs, since SequentialAgent can't skip a step, but only
actually does anything when the officer approved the application. This
is the same pattern Lesson 11a and 11b's decision agents used, an
agent that checks whether its own work applies before doing it.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import generate_loan_offer_letter

instruction = """You are the disbursement agent for a loan approval
pipeline at a retail bank.

Session state has:

Officer decision: {officer_decision?}
Credit result: {credit_result}
Risk result: {risk_result}

If officer_decision is exactly "APPROVE", call
`generate_loan_offer_letter` with the applicant's name, loan_amount,
tenure_months from the credit result, and an interest_rate of 10.5.
Then briefly confirm the letter was generated.

If officer_decision is anything else, "REJECT", "REFER", or missing,
do not call the tool. Just note in one sentence that disbursement
doesn't apply to this application.
"""

disbursement_agent = Agent(
    name="disbursement_agent",
    model=get_model("primary"),
    description="Generates a loan offer letter PDF if the officer approved the application.",
    instruction=instruction,
    tools=[generate_loan_offer_letter],
)
