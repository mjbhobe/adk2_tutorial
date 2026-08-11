"""Lesson 14a: Run both Stripe MCP agents.

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
from mcp_demo.agent import stripe_refund_agent, stripe_research_agent

RESEARCH_APP = "lesson14a_stripe_research"
REFUND_APP = "lesson14a_stripe_refund"
USER_ID = "console_user"


async def run_research_demo() -> None:
    """Runs one fixed query through the plain, always-available Stripe MCP agent."""
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())
    query = "What's the current Stripe account information for this account?"

    print("=== Example 1: plain consuming (every Stripe tool always available) ===")
    print(f"Query: {query}\n")

    response = await run_agent_query(
        agent=stripe_research_agent,
        app_name=RESEARCH_APP,
        user_id=USER_ID,
        session_id=session_id,
        query=query,
        session_service=session_service,
    )
    print("Response:", response)
    print()


async def run_refund_loop() -> None:
    """Runs an interactive loop against the skill-gated refund agent."""
    session_service = InMemorySessionService()

    print("=== Example 2: skill-gated (create_refund only appears once loaded) ===")
    print("Try a refund request with a charge ID and a reason. Type 'quit' to exit.\n")

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
            agent=stripe_refund_agent,
            app_name=REFUND_APP,
            user_id=USER_ID,
            session_id=session_id,
            query=user_input,
            session_service=session_service,
        )
        print("Agent:", response, "\n")


async def main() -> None:
    await run_research_demo()
    await run_refund_loop()


if __name__ == "__main__":
    asyncio.run(main())
