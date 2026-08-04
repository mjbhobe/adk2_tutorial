"""Lesson 11b: Run the KYC onboarding pipeline (ParallelAgent + decision).

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
from kyc_pipeline.agent import root_agent

APP_NAME = "lesson11b_parallel_agent"


async def main() -> None:
    """Runs the KYC onboarding pipeline against console input."""
    session_service = InMemorySessionService()
    user_id = "console_user"

    print("KYC onboarding pipeline (ParallelAgent, then decision).")
    print("Paste a KYC application as free text, or type 'quit' to exit.\n")

    loop = asyncio.get_event_loop()
    while True:
        try:
            user_input = await loop.run_in_executor(None, lambda: input("Application: "))
        except EOFError:
            break

        if user_input.strip().lower() in ("quit", "exit"):
            break

        # A fresh session per application: each KYC check is a one-shot
        # run, not an ongoing conversation.
        session_id = str(uuid.uuid4())

        await run_agent_query(
            agent=root_agent,
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            query=user_input,
            session_service=session_service,
        )

        # The three parallel branches interleave their events, so
        # run_agent_query's single "final response" text is only
        # reliable here because it's the decision agent, the sequential
        # step running after the parallel one, that produces the actual
        # final response. Still read every result back from session
        # state, so the three checks that fed the decision are visible
        # too, not just the outcome.
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        print("\nCredit bureau:  ", session.state.get("credit_bureau_result"))
        print("Fraud watchlist:", session.state.get("fraud_watchlist_result"))
        print("KYC documents:  ", session.state.get("kyc_document_result"))
        print("Decision:       ", session.state.get("kyc_decision_result"))
        print()


if __name__ == "__main__":
    asyncio.run(main())
