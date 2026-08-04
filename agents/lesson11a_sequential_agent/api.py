"""Lesson 11a: FastAPI server for the loan underwriting SequentialAgent.

Wraps the same SequentialAgent pipeline main.py drives, this time behind
an HTTP API any client can call, a Streamlit form, a bank's real customer
portal, or anything else, without needing to know ADK exists underneath.

session_service is created once at module load time and shared across
every request, exactly as in Lesson 9's main.py. Creating a fresh one
per request would wipe state before we ever got to read it back out.

Run with:
    uv run agents/lesson11a_sequential_agent/api.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # adds agents/ for common.*

from fastapi import FastAPI
from google.adk.sessions import InMemorySessionService

from common.runner_utils import run_agent_query
from loan_pipeline.agent import root_agent
from loan_pipeline.sub_agents.intake_agent.agent import IntakeResult
from loan_pipeline.sub_agents.credit_check_agent.agent import CreditCheckResult
from loan_pipeline.sub_agents.risk_scoring_agent.agent import RiskScoringResult
from loan_pipeline.sub_agents.decision_agent.agent import DecisionResult
from pydantic import BaseModel

APP_NAME = "lesson11a_sequential_agent"

# Created once, shared across every HTTP request, same pattern as Lesson 9.
session_service = InMemorySessionService()
app = FastAPI(title="Loan Underwriting Pipeline API")


class ApplicationRequest(BaseModel):
    """The shape of an incoming request to /apply."""

    user_id: str
    session_id: str
    application_text: str


class ApplicationResponse(BaseModel):
    """The shape of a response from /apply.

    Returns all four sub-agents' results, not just the final decision.
    SequentialAgent runs every step in order and can't skip any of them
    conditionally, so all four are always populated in session state by
    the time a run completes, and all four are worth showing the caller.
    """

    intake: IntakeResult
    credit_check: CreditCheckResult
    risk_scoring: RiskScoringResult
    decision: DecisionResult


@app.get("/health")
async def health() -> dict:
    """Simple liveness check, useful once this is deployed."""
    return {"status": "ok"}


@app.post("/apply", response_model=ApplicationResponse)
async def apply(request: ApplicationRequest) -> ApplicationResponse:
    """Runs one loan application through the full pipeline and returns every step's result."""
    await run_agent_query(
        agent=root_agent,
        app_name=APP_NAME,
        user_id=request.user_id,
        session_id=request.session_id,
        query=request.application_text,
        session_service=session_service,
    )

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=request.user_id, session_id=request.session_id
    )

    return ApplicationResponse(
        intake=session.state["intake_result"],
        credit_check=session.state["credit_check_result"],
        risk_scoring=session.state["risk_scoring_result"],
        decision=session.state["decision_result"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)