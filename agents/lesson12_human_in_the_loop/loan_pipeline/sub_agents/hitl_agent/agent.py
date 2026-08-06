"""Lesson 12: HITL agent, the human checkpoint in the loan approval pipeline.

Deliberately has no output_schema or output_key. The officer's real
decision doesn't travel through this agent's own structured output,
it gets written to session state directly by pipeline_runner.py when
the pipeline resumes, the same tool-writes-state-directly pattern
Lesson 11c settled on after the SetModelResponseTool reliability
problems there. This agent's own final response is just a plain-text
acknowledgement.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import request_officer_approval_tool

instruction = """You are the human-in-the-loop checkpoint for a loan
approval pipeline at a retail bank. Your job is not to decide anything
yourself, it's to hand the case to a human officer and wait.

Session state has the credit and risk agents' results:

Credit result:
{credit_result}

Risk result:
{risk_result}

Call `request_officer_approval` exactly once, with the applicant's
name, pan_number, loan_amount, credit_score, and risk_band pulled from
those two results.

If this is the first time you're running, that call will pause the
pipeline, a human officer hasn't decided anything yet. If you're seeing
this because the pipeline was resumed, the tool's result now reflects
the officer's real decision, acknowledge it briefly in plain text, no
special formatting required.
"""

hitl_agent = Agent(
    name="hitl_agent",
    model=get_model("primary"),
    description="Pauses the pipeline for a human loan officer's approve, reject, or refer decision.",
    instruction=instruction,
    tools=[request_officer_approval_tool],
)
