"""Lesson 12: FastAPI server for the loan approval pipeline.

Two endpoints, /apply and /officer-decision, both thin wrappers around
pipeline_runner.py's two functions, the same ones main.py calls
directly. This is what guarantees the console and the web front end
behave identically, neither one talks to Runner or the session service
on its own.

Run with:
    uv run agents/lesson12_human_in_the_loop/api.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)  # adds agents/ for common.*

from fastapi import FastAPI
from google.adk.sessions import InMemorySessionService
from pydantic import BaseModel

from loan_pipeline.pipeline_runner import submit_application, submit_officer_decision

# Created once, shared across every HTTP request, same pattern as every
# other api.py in this series. This is what lets a later
# /officer-decision request find the session an earlier /apply request
# paused.
session_service = InMemorySessionService()
app = FastAPI(title="Loan Approval Pipeline API")


class ApplicationRequest(BaseModel):
    """The shape of an incoming request to /apply."""

    user_id: str
    session_id: str
    application_text: str


class DecisionRequest(BaseModel):
    """The shape of an incoming request to /officer-decision."""

    user_id: str
    session_id: str
    decision: str


@app.get("/health")
async def health() -> dict:
    """Simple liveness check, useful once this is deployed."""
    return {"status": "ok"}


@app.post("/apply")
async def apply(request: ApplicationRequest) -> dict:
    """Submits a loan application, running it up to the officer checkpoint."""
    return await submit_application(
        request.application_text, request.user_id, request.session_id, session_service
    )


@app.post("/officer-decision")
async def officer_decision(request: DecisionRequest) -> dict:
    """Submits a loan officer's decision, resuming a paused application."""
    return await submit_officer_decision(
        request.decision, request.user_id, request.session_id, session_service
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8083)
