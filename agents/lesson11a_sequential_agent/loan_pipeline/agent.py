"""Lesson 11a: SequentialAgent that chains the loan underwriting pipeline.

Runs intake, credit check, risk scoring, and decision agents in a fixed
order, using session state to pass each step's output to the next.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import SequentialAgent

from .sub_agents.intake_agent.agent import intake_agent
from .sub_agents.credit_check_agent.agent import credit_check_agent
from .sub_agents.risk_scoring_agent.agent import risk_scoring_agent
from .sub_agents.decision_agent.agent import decision_agent

root_agent = SequentialAgent(
    name="loan_underwriting_pipeline",
    description="Runs a loan application through intake, credit check, risk scoring, and decision, in order.",
    sub_agents=[
        intake_agent,
        credit_check_agent,
        risk_scoring_agent,
        decision_agent,
    ],
)
