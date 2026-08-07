"""Lesson 11d: Run both AgentTool examples.

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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # adds agents/ for common.*

from google.adk.sessions import InMemorySessionService

from common.runner_utils import run_agent_query
from research_pipeline.agent import root_agent as research_agent
from support_pipeline.agent import root_agent as support_agent

RESEARCH_APP = "lesson11d_research"
SUPPORT_APP = "lesson11d_support"
USER_ID = "console_user"


async def run_research_demo() -> None:
    """Runs one fixed query through the Gemini-backed search specialist, via AgentTool."""
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())
    query = "What's today's date, and who is the current Prime Minister of India?"

    print("=== Example 1: platform-forced (Gemini search specialist) ===")
    print(f"Query: {query}\n")

    response = await run_agent_query(
        agent=research_agent,
        app_name=RESEARCH_APP,
        user_id=USER_ID,
        session_id=session_id,
        query=query,
        session_service=session_service,
    )
    print("Response:", response)
    print()


async def run_support_loop() -> None:
    """Runs an interactive loop against the routing customer support agent."""
    session_service = InMemorySessionService()

    print("=== Example 2: routing (customer support agent) ===")
    print("Ask about a balance, or report a lost/stolen card. Type 'quit' to exit.\n")

    loop = asyncio.get_event_loop()
    while True:
        try:
            user_input = await loop.run_in_executor(None, lambda: input("You: "))
        except EOFError:
            break

        if user_input.strip().lower() in ("quit", "exit"):
            break

        session_id = str(uuid.uuid4())
        response = await run_agent_query(
            agent=support_agent,
            app_name=SUPPORT_APP,
            user_id=USER_ID,
            session_id=session_id,
            query=user_input,
            session_service=session_service,
        )
        print("Agent:", response, "\n")


async def main() -> None:
    await run_research_demo()
    await run_support_loop()


if __name__ == "__main__":
    asyncio.run(main())
