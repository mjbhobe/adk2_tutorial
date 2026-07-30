"""Lesson 7a: Callbacks in Practice.

Drives the wealth management advisory agent with a pre-seeded session
(simulating a CRM handoff, as in Lesson 6a) so the agent immediately
knows the customer's name and tier. The memory service is wired in so
after_agent_callback's call to add_session_to_memory() actually has
somewhere to persist data.

Run with:
    uv run agents/lesson07a_callbacks/main.py

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.genai import types

from wealth_advisor.agent import root_agent

APP_NAME = "wealth_advisor_app"
USER_ID = "demo_user"


async def main() -> None:
    """Runs a console wealth advisory conversation with all six callbacks active."""
    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()

    # Pre-seed CRM context exactly as Lesson 6a did, so the agent
    # knows who it's talking to before the first message.
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={
            "customer_name": "Arjun Mehta",
            "account_tier": "Platinum",
            "customer_id": "CUST001",
        },
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
        memory_service=memory_service,  # Required for after_agent_callback's
    )  # add_session_to_memory() to work.

    print("Wealth Management Advisor (type 'exit' to quit)\n")
    print(
        f"Customer: {session.state['customer_name']} "
        f"({session.state['account_tier']})\n"
    )

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        user_message = types.Content(role="user", parts=[types.Part(text=user_input)])

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

        # Show live session state so you can watch callbacks mutating it.
        updated = await session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session.id
        )
        print(
            f"[state] turn_count={updated.state.get('turn_count')} | "
            f"audit_log entries={len(updated.state.get('audit_log', []))}\n"
        )


if __name__ == "__main__":
    asyncio.run(main())
