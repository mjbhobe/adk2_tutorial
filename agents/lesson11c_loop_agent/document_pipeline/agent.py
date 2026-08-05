"""Lesson 11c: LoopAgent that retries Aadhaar document verification.

Repeats document_review_agent until it either signals escalate (the
document passed) or max_iterations is reached (three attempts, then
the case goes to a human regardless of what the last attempt found).

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import LoopAgent

from .sub_agents.document_review_agent.agent import document_review_agent

root_agent = LoopAgent(
    name="document_retry_loop",
    description="Retries Aadhaar document verification up to three times, or until it passes.",
    sub_agents=[document_review_agent],
    max_iterations=3,
)
