"""Lesson 7b: Long-Running Tools — credit bureau check.

Demonstrates how LongRunningFunctionTool surfaces an in-progress
state to the application while the slow operation runs, rather than
freezing the conversation until it completes.

Run with:
    uv run agents/lesson07b_long_running_tools/main.py
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

# adds agents/ folder to sys.path → for common.* 
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from credit_check.agent import root_agent

APP_NAME = "credit_check_app"
USER_ID = "demo_user"


async def main() -> None:
    """Runs a console loan processing conversation with a long-running tool."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
    )

    print("Loan Processing Assistant (type 'exit' to quit)\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        user_message = types.Content(
            role="user", parts=[types.Part(text=user_input)]
        )

        # Unlike earlier lessons, we do NOT break on the first
        # is_final_response() event. With a long-running tool, two
        # events carry is_final_response()=True in one turn:
        #   1. The model's "check is running" message (before tool completes)
        #   2. The model's result summary (after tool completes)
        # Collecting all final-response text and printing it at the end
        # gives the user a coherent, complete answer.
        response_parts = []
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session.id,
            new_message=user_message,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                text = "".join(
                    part.text for part in event.content.parts if part.text
                )
                if text:
                    response_parts.append(text)

        if response_parts:
            print(f"Agent: {' '.join(response_parts)}\n")


if __name__ == "__main__":
    asyncio.run(main())
