"""Lesson 11b: KYC onboarding pipeline, fan out then merge.

The root agent is a SequentialAgent with two steps. The first step is a
ParallelAgent, the credit bureau, fraud watchlist, and KYC document
checks, running concurrently exactly as before. The second step is the
decision agent, reading all three results after the parallel step
completes and producing a final onboarding outcome.

This is the shape a standalone ParallelAgent almost never appears in on
its own: independent checks are only useful once something downstream
looks at all of them together. SequentialAgent and ParallelAgent nest
freely, a ParallelAgent can be one step of a SequentialAgent's sequence,
which is exactly what's happening here.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import ParallelAgent, SequentialAgent

from .sub_agents.credit_bureau_agent.agent import credit_bureau_agent
from .sub_agents.fraud_watchlist_agent.agent import fraud_watchlist_agent
from .sub_agents.kyc_document_agent.agent import kyc_document_agent
from .sub_agents.kyc_decision_agent.agent import kyc_decision_agent

kyc_checks = ParallelAgent(
    name="kyc_onboarding_checks",
    description="Runs credit bureau, fraud watchlist, and KYC document checks concurrently for new customer onboarding.",
    sub_agents=[credit_bureau_agent, fraud_watchlist_agent, kyc_document_agent],
)

root_agent = SequentialAgent(
    name="kyc_onboarding_pipeline",
    description="Runs the three KYC checks concurrently, then applies the onboarding decision rules to the combined result.",
    sub_agents=[kyc_checks, kyc_decision_agent],
)
