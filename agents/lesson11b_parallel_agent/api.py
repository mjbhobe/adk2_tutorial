"""Lesson 11b: FastAPI server for the KYC onboarding pipeline.

Same shape as Lesson 11a's api.py: a shared session_service, a thin
endpoint, and the response built from session.state after the run
completes. All four results (the three parallel checks plus the final
decision) are read back from state rather than trusted from
run_agent_query's single "final response" text, so the response stays
consistent even though, with this pipeline's SequentialAgent-wrapping-
ParallelAgent shape, that text happens to be reliable now (it's the
decision agent, running after the parallel step, that produces it).

Run with:
    uv run agents/lesson11b_parallel_agent/api.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # adds agents/ for common.*

from fastapi import FastAPI
from google.adk.sessions import InMemorySessionService
from pydantic import BaseModel

from common.runner_utils import run_agent_query
from kyc_pipeline.agent import root_agent
from kyc_pipeline.sub_agents.credit_bureau_agent.agent import CreditBureauResult
from kyc_pipeline.sub_agents.fraud_watchlist_agent.agent import FraudWatchlistResult
from kyc_pipeline.sub_agents.kyc_document_agent.agent import KycDocumentResult
from kyc_pipeline.sub_agents.kyc_decision_agent.agent import KycDecisionResult

APP_NAME = "lesson11b_parallel_agent"

# Created once, shared across every HTTP request, same pattern as Lesson 9 and 11a.
session_service = InMemorySessionService()
app = FastAPI(title="KYC Onboarding Pipeline API")


class KycRequest(BaseModel):
    """The shape of an incoming request to /kyc-check."""

    user_id: str
    session_id: str
    application_text: str


class KycResponse(BaseModel):
    """The shape of a response from /kyc-check.

    All three parallel checks are returned alongside the final decision,
    so a caller can see both what was found and what it added up to.
    """

    credit_bureau: CreditBureauResult
    fraud_watchlist: FraudWatchlistResult
    kyc_document: KycDocumentResult
    decision: KycDecisionResult


@app.get("/health")
async def health() -> dict:
    """Simple liveness check, useful once this is deployed."""
    return {"status": "ok"}


@app.post("/kyc-check", response_model=KycResponse)
async def kyc_check(request: KycRequest) -> KycResponse:
    """Runs the full KYC pipeline (parallel checks, then decision) and returns every result."""
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

    return KycResponse(
        credit_bureau=session.state["credit_bureau_result"],
        fraud_watchlist=session.state["fraud_watchlist_result"],
        kyc_document=session.state["kyc_document_result"],
        decision=session.state["kyc_decision_result"],
    )


if __name__ == "__main__":
    import uvicorn

    # A different port from Lesson 11a's api.py (8080), so both can run
    # side by side without clashing.
    uvicorn.run(app, host="127.0.0.1", port=8081)
