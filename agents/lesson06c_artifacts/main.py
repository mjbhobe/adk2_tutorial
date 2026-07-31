"""Lesson 6c: Artifacts — loan summary PDF generator.

Demonstrates saving and retrieving a binary artifact (a PDF) from
inside an async tool function. After each turn, main.py checks
whether an artifact was saved via the event's artifact_delta, and
if so, retrieves it from the artifact service and writes it to disk.

Run with:
    uv run agents/lesson06c_artifacts/main.py
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from loan_report.agent import root_agent

APP_NAME = "loan_report_app"
USER_ID = "demo_user"


async def main() -> None:
    """Runs a console loan report session, saving any generated PDFs to disk."""
    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
        artifact_service=artifact_service,  # Required for save/load_artifact to work.
    )

    print("Loan Report Agent (type 'exit' to quit)\n")

    loop = asyncio.get_event_loop()

    while True:
        try:
            user_input = await loop.run_in_executor(None, lambda: input("You: "))
        except EOFError:
            break

        user_input = user_input.strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        user_message = types.Content(
            role="user", parts=[types.Part(text=user_input)]
        )

        saved_artifact_filename = None

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

            # artifact_delta is a dict of {filename: version} for any
            # artifacts saved during this turn. We capture the filename
            # here so we can retrieve the artifact after the turn ends.
            if (
                hasattr(event, "actions")
                and event.actions
                and event.actions.artifact_delta
            ):
                saved_artifact_filename = list(
                    event.actions.artifact_delta.keys()
                )[0]

        # Once the turn is complete, retrieve the artifact and write to disk.
        if saved_artifact_filename:
            artifact_part = await artifact_service.load_artifact(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=session.id,
                filename=saved_artifact_filename,
            )
            if artifact_part and artifact_part.inline_data and artifact_part.inline_data.data:
                out_path = Path(saved_artifact_filename)
                out_path.write_bytes(artifact_part.inline_data.data)
                print(f"[PDF saved to: {out_path.resolve()}]\n")


if __name__ == "__main__":
    asyncio.run(main())