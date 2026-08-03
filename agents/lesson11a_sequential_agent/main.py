"""Lesson 11a: Run the loan underwriting SequentialAgent pipeline.

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
from loan_pipeline.agent import root_agent

APP_NAME = "lesson11a_sequential_agent"


async def main() -> None:
    """Runs the loan underwriting pipeline against console input."""
    session_service = InMemorySessionService()
    user_id = "console_user"
    session_id = str(uuid.uuid4())

    print("Loan underwriting pipeline (SequentialAgent).")
    print("Paste a loan application as free text, or type 'quit' to exit.\n")

    loop = asyncio.get_event_loop()
    while True:
        try:
            user_input = await loop.run_in_executor(None, lambda: input("Application: "))
        except EOFError:
            break

        if user_input.strip().lower() in ("quit", "exit"):
            break

        response = await run_agent_query(
            agent=root_agent,
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            query=user_input,
            session_service=session_service,
        )
        print(f"\nPipeline: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
