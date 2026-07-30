"""Lesson 8: Long-Term Memory.

Demonstrates cross-session memory recall by running two separate
sessions within one process. Session 1 establishes client preferences;
Session 2 starts completely fresh but the agent recalls those
preferences via the load_memory tool, because both sessions share the
same InMemoryMemoryService instance.

Run with:
    uv run agents/lesson08_long_term_memory/main.py
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

from relationship_manager.agent import root_agent

APP_NAME = "wealth_mgmt_app"
USER_ID = "client_001"


async def run_session(
    runner: Runner,
    session_service: InMemorySessionService,
    label: str,
    prompts: list[str],
) -> None:
    """Creates a fresh session and runs a list of prompts through it.

    Args:
        runner: The shared Runner instance.
        session_service: The shared session service.
        label: A descriptive label printed as a section header.
        prompts: The list of user messages to send in sequence.
    """
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"  Session ID: {session.id[:16]}...")
    print(f"{'=' * 60}\n")

    loop = asyncio.get_event_loop()

    for prompt in prompts:
        try:
            user_input = await loop.run_in_executor(
                None, lambda p=prompt: p  # use pre-set prompts in demo mode
            )
        except EOFError:
            break

        print(f"You: {user_input}")
        user_message = types.Content(
            role="user", parts=[types.Part(text=user_input)]
        )

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


async def interactive_session(
    runner: Runner,
    session_service: InMemorySessionService,
    label: str,
) -> None:
    """Creates a fresh session and runs an interactive console loop.

    Args:
        runner: The shared Runner instance.
        session_service: The shared session service.
        label: A descriptive label printed as a section header.
    """
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"  Session ID: {session.id[:16]}...")
    print(f"{'=' * 60}\n")
    print("Type 'done' when finished with this session.\n")

    loop = asyncio.get_event_loop()

    while True:
        try:
            user_input = await loop.run_in_executor(None, lambda: input("You: "))
        except EOFError:
            break

        user_input = user_input.strip()
        if user_input.lower() in {"done", "exit", "quit"}:
            break
        if not user_input:
            continue

        user_message = types.Content(
            role="user", parts=[types.Part(text=user_input)]
        )

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


async def main() -> None:
    """Runs a two-session memory recall demonstration.

    Both sessions share one InMemoryMemoryService. Session 1 establishes
    client preferences; Session 2 is completely fresh but the agent
    recalls those preferences via load_memory.
    """
    # Both services are created once and shared across all sessions.
    # This is what makes memory persist between Session 1 and Session 2.
    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()

    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
        memory_service=memory_service,  # Required for load_memory and
    )                                   # add_session_to_memory() to work.

    print("Relationship Manager Assistant — Long-Term Memory Demo")
    print("=" * 60)
    print("This demo runs two separate sessions.")
    print("Session 1: you tell the agent your investment preferences.")
    print("Session 2: a fresh session where the agent should recall them.")
    print("=" * 60)

    # ── Session 1: client states preferences ──────────────────────────
    # Run this as a scripted demo so the lesson is reproducible.
    await run_session(
        runner,
        session_service,
        "SESSION 1  —  Client states preferences",
        prompts=[
            "I prefer conservative, low-risk investments and I'm particularly "
            "interested in ESG and sustainable funds.",
            "I also want to avoid any exposure to fossil fuels or tobacco companies.",
        ],
    )

    print("\n[Session 1 complete. Preferences saved to memory.]")
    print("[Starting Session 2 — this is a completely fresh conversation.]\n")
    input("Press Enter to begin Session 2...")

    # ── Session 2: fresh session, agent should recall from memory ─────
    await interactive_session(
        runner,
        session_service,
        "SESSION 2  —  Fresh session, testing memory recall",
    )

    print("\nDemo complete.")
    print("In Session 2, the agent should have recalled your ESG preference")
    print("and fossil-fuel exclusion without you repeating them.")


if __name__ == "__main__":
    asyncio.run(main())
