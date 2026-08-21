"""Lesson 15a: The risk specialist, exposed as an A2A server.

Run this file directly, it's a standalone server, not something
adk web or another agent's main.py imports.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parents[1]))  # adds agents/ for common.*
sys.path.insert(0, str(THIS_DIR.parent))  # adds lesson15a_a2a/ for risk_service.*

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent

from common.model_config import get_model
from risk_service.tools import calculate_risk_score

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

app = to_a2a(risk_specialist_agent, host="localhost", port=8001)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
