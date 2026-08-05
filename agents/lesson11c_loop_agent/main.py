"""Lesson 11c: Run the document verification LoopAgent pipeline.

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

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)  # adds agents/ for common.*

from google.adk.sessions import InMemorySessionService

from common.runner_utils import run_agent_query
from document_pipeline.agent import root_agent

APP_NAME = "lesson11c_loop_agent"


async def main() -> None:
    """Runs the document retry loop against console input."""
    session_service = InMemorySessionService()
    user_id = "console_user"

    print("Document verification (LoopAgent, up to 3 attempts).")
    print("Paste an applicant's name and Aadhaar number, or type 'quit' to exit.\n")

    loop = asyncio.get_event_loop()
    while True:
        try:
            user_input = await loop.run_in_executor(
                None, lambda: input("Application: ")
            )
        except EOFError:
            break

        if user_input.strip().lower() in ("quit", "exit"):
            break

        # A fresh session per application: each document check is a
        # one-shot run, not an ongoing conversation.
        session_id = str(uuid.uuid4())

        await run_agent_query(
            agent=root_agent,
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            query=user_input,
            session_service=session_service,
        )

        # Unlike Lesson 11b's ParallelAgent, there's no race here,
        # LoopAgent runs one turn at a time, so run_agent_query's final
        # response text really is whichever attempt ran last. State is
        # still the better place to read the result from, though: it's
        # already a parsed dict with attempt_number, passed, and issue
        # as separate fields, rather than a block of text to parse by hand.
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

        # show intermediate "retry" attempts, if any
        for event in session.events:
            attempt = event.actions.state_delta.get("document_check_result")
            if attempt:
                print(" attempt:", attempt)

        result = session.state.get("document_check_result")
        print("\nFinal result:", result)
        if result and result.get("passed"):
            print(f"Verified after {result['attempt_number']} attempt(s).")
        else:
            print("Retries exhausted without a pass. Refer to manual review.")
        print()


if __name__ == "__main__":
    asyncio.run(main())
