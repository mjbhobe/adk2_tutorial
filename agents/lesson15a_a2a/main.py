"""Lesson 15a: Run both consuming patterns against the risk service.

Start risk_service/agent.py first, in a separate terminal, before
running this.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import asyncio
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))  # adds agents/ for common.*
sys.path.insert(0, str(THIS_DIR))  # adds this lesson's own folder for loan_orchestrator

from google.adk.sessions import InMemorySessionService

from common.runner_utils import run_agent_query
from loan_orchestrator.agent import loan_pipeline, root_agent

APP_NAME = "lesson15a_a2a"
USER_ID = "console_user"
QUERY = (
    "Full risk check please: credit score 773, annual income 900000, "
    "loan amount 500000, tenure 36 months, no prior defaults."
)


async def run_agent_tool_demo() -> None:
    """Runs the query against the AgentTool-based orchestrator."""
    print("=== Pattern 1: AgentTool (a model's own judgment call) ===\n")
    session_service = InMemorySessionService()
    response = await run_agent_query(
        agent=root_agent,
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=str(uuid.uuid4()),
        query=QUERY,
        session_service=session_service,
    )
    print("Response:", response)
    print()


async def run_sequential_demo() -> None:
    """Runs the same query through the fixed intake-then-assess pipeline."""
    print("=== Pattern 2: plain sub-agent in a fixed SequentialAgent pipeline ===\n")
    session_service = InMemorySessionService()
    response = await run_agent_query(
        agent=loan_pipeline,
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=str(uuid.uuid4()),
        query=QUERY,
        session_service=session_service,
    )
    print("Response:", response)
    print()


async def main() -> None:
    await run_agent_tool_demo()
    await run_sequential_demo()


if __name__ == "__main__":
    asyncio.run(main())
