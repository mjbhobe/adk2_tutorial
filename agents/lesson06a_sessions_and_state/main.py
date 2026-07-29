"""Lesson 6a: Sessions & State.

Builds a SessionService, a Session pre-seeded with CRM-style customer
context, and a Runner by hand, then drives a console conversation loop
manually, exactly what adk run has been doing for you invisibly since
Lesson 2.

Run with:
    uv run agents/lesson06a_sessions_and_state/main.py

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load API keys from the project-root .env before importing any ADK
# modules that depend on them. adk run/adk web did this automatically;
# in our own main.py we have to do it ourselves.
load_dotenv(override=True)

# this line is required to bring the agents folder (parents[1]) into
# sys.path, because our utility modules sit inside that folder.
# adk run/adk web automatically added the agents folder to sys.path/
# Since we are running main.py directly, we need to add this line!
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from priority_support.agent import root_agent

APP_NAME = "priority_support_app"
USER_ID = "demo_user"


async def main() -> None:
    """Sets up a pre-seeded session, then runs a console chat loop against it."""

    session_service = InMemorySessionService()

    # This is the moment adk run can't show you: a session created with
    # its state already populated, simulating a real handoff from a
    # bank's CRM system before the conversation even begins.
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={
            "customer_name": "Arjun Mehta",
            "account_tier": "Platinum",
            "relationship_manager_name": "Kavita Rao",
        },
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
    )

    print("Hello, I am the Priority Support Assistant. How can I help you?")
    print("Type in your query (or type 'exit' to quit)\n")

    while True:
        user_input = input("Query: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        user_message = types.Content(role="user", parts=[types.Part(text=user_input)])

        # Runner.run_async is an async generator, not a function that
        # returns one value: it yields one Event per step of the turn as
        # it happens (tool calls, tool results, partial and final text).
        # `async for` consumes that stream as it arrives. This exact loop
        # is what adk run and adk web have been running for you this
        # whole series, just never shown to you directly until now.
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session.id,
            new_message=user_message,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = "".join(
                    part.text for part in event.content.parts if part.text
                )
                print(f"Agent: {response_text}\n")


if __name__ == "__main__":
    asyncio.run(main())