"""Lesson 11c: FastAPI server for the document verification LoopAgent.

Same shape as Lesson 11a's and 11b's api.py: a shared session_service, a
thin endpoint, run_agent_query to drive the run, and the response read
back from session.state.

Run with:
    uv run agents/lesson11c_loop_agent/api.py
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
from document_pipeline.agent import root_agent
from document_pipeline.sub_agents.document_review_agent.agent import DocumentCheckResult

APP_NAME = "lesson11c_loop_agent"

# Created once, shared across every HTTP request, same pattern as Lesson 9, 11a, and 11b.
session_service = InMemorySessionService()
app = FastAPI(title="Document Verification Loop API")


class DocumentCheckRequest(BaseModel):
    """The shape of an incoming request to /verify-document."""

    user_id: str
    session_id: str
    application_text: str


class DocumentCheckResponse(BaseModel):
    """The shape of a response from /verify-document.

    result is whichever attempt the loop ended on, either the one that
    passed, or the final attempt if all three failed.
    """

    result: DocumentCheckResult


@app.get("/health")
async def health() -> dict:
    """Simple liveness check, useful once this is deployed."""
    return {"status": "ok"}


@app.post("/verify-document", response_model=DocumentCheckResponse)
async def verify_document(request: DocumentCheckRequest) -> DocumentCheckResponse:
    """Runs the document retry loop and returns the final attempt's result."""
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

    return DocumentCheckResponse(result=session.state["document_check_result"])


if __name__ == "__main__":
    import uvicorn

    # A different port from Lesson 11a (8080) and 11b (8081).
    uvicorn.run(app, host="127.0.0.1", port=8082)
