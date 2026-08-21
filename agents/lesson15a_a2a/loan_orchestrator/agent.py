"""Lesson 15a: Two ways of consuming the remote risk_specialist_agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools.agent_tool import AgentTool

from common.model_config import get_model

# Same RemoteA2aAgent instance, two different roles below. The URL points
# at risk_service/agent.py's own server, which must already be running,
# in a separate terminal, before either of these is used.
remote_risk_agent = RemoteA2aAgent(
    name="risk_assessment_agent",
    agent_card="http://127.0.0.1:8001/.well-known/agent-card.json",
)


# --- Pattern 1: AgentTool, for a model's own judgment call. ---

orchestrator_instruction = """You are a loan support assistant. When a
customer gives you enough detail for a full risk assessment, credit
score, annual income, loan amount, tenure, and default history, all
five, delegate to the risk assessment agent tool. For anything else,
including a request missing one of those five details, ask for what's
missing instead of guessing or calling the tool anyway.
"""

root_agent = Agent(
    name="loan_orchestrator",
    model=get_model("primary"),
    description="Loan support assistant that delegates full risk assessments to a remote A2A agent.",
    instruction=orchestrator_instruction,
    tools=[AgentTool(agent=remote_risk_agent)],
)


# --- Pattern 2: plain sub-agent, for a step that always runs. ---

intake_agent = Agent(
    name="intake_agent",
    model=get_model("primary"),
    description="Confirms an applicant's details are complete before risk assessment.",
    instruction="""Read the applicant's credit_score, annual_income,
loan_amount, tenure_months, and has_defaults from the user's message
and restate them plainly, so the next step has a clear record of what's
being assessed. Don't calculate anything yourself.
""",
)

loan_pipeline = SequentialAgent(
    name="loan_pipeline",
    sub_agents=[intake_agent, remote_risk_agent],
)
