# agents/lesson12_human_in_the_loop/loan_pipeline/agent.py
"""Lesson 12: The loan approval pipeline, split into two apps.

review_pipeline (resumable): credit -> risk -> HITL. This is the part
that pauses.

outcome_pipeline (not resumable, doesn't need to be): disbursement ->
referral. pipeline_runner.py drives this explicitly, right after
resuming review_pipeline, against the same session.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import SequentialAgent
from google.adk.apps import App, ResumabilityConfig

from .sub_agents.credit_agent.agent import credit_agent
from .sub_agents.risk_agent.agent import risk_agent
from .sub_agents.hitl_agent.agent import hitl_agent
from .sub_agents.disbursement_agent.agent import disbursement_agent
from .sub_agents.referral_agent.agent import referral_agent

APP_NAME = "lesson12_human_in_the_loop"

review_pipeline = SequentialAgent(
    name="loan_review_pipeline",
    description="Runs credit check and risk scoring, then pauses for a human officer's decision.",
    sub_agents=[credit_agent, risk_agent, hitl_agent],
)

review_app = App(
    name=APP_NAME,
    root_agent=review_pipeline,
    resumability_config=ResumabilityConfig(is_resumable=True),
)

outcome_pipeline = SequentialAgent(
    name="loan_outcome_pipeline",
    description="Generates a disbursement letter or a referral task based on the officer's decision.",
    sub_agents=[disbursement_agent, referral_agent],
)

outcome_app = App(
    name=APP_NAME,
    root_agent=outcome_pipeline,
)

# adk web / adk run look for a variable named root_agent. review_pipeline
# is the one worth pointing those tools at, it's the part that pauses.
root_agent = review_pipeline
