"""Lesson 9: Production Serving.

A FastAPI server wrapping the relationship manager agent from Lesson 8.
This is the production-shaped way to run an ADK agent: as a long-lived
API server called by other systems over HTTP, rather than through
adk run's interactive CLI or adk web's browser UI.

Three objects are created once at module load time and shared across
every request: the FastAPI app, the session service, and the memory
service. Creating fresh instances per request would wipe all state
on every call, breaking multi-turn conversations entirely.

Run with:
    uv run agents/lesson09_production_serving/main.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from pydantic import BaseModel

from common.runner_utils import run_agent_query
from lesson08_long_term_memory.relationship_manager.agent import root_agent

APP_NAME = "wealth_management_app"

# All three created once, shared across every HTTP request.
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()
app = FastAPI(title="Relationship Manager Agent API")


class ChatRequest(BaseModel):
    """The shape of an incoming request to /chat."""

    user_id: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    """The shape of a response from /chat."""

    response: str


@app.get("/health")
async def health() -> dict:
    """Simple liveness check, useful once this is deployed."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Sends one message to the agent and returns its reply."""
    response_text = await run_agent_query(
        agent=root_agent,
        app_name=APP_NAME,
        user_id=request.user_id,
        session_id=request.session_id,
        query=request.message,
        session_service=session_service,
        memory_service=memory_service,
    )
    return ChatResponse(response=response_text)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)