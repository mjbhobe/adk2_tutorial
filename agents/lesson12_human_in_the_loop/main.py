"""Lesson 12: Run the loan approval pipeline, pausing for officer sign-off.

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

from loan_pipeline.pipeline_runner import submit_application, submit_officer_decision

USER_ID = "console_user"


async def main() -> None:
    """Runs one loan application through the pipeline, pausing for a human decision."""
    session_service = InMemorySessionService()

    print("Loan approval pipeline (Human-in-the-Loop).")
    print("Paste a loan application as free text, or type 'quit' to exit.\n")

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

        session_id = str(uuid.uuid4())

        result = await submit_application(
            user_input, USER_ID, session_id, session_service
        )

        if result["status"] != "pending_officer_review":
            print("Unexpected: pipeline completed without pausing.", result)
            continue

        print("\n--- Pending officer review ---")
        print("Credit result:", result["credit_result"])
        print("Risk result:  ", result["risk_result"])

        decision = None
        while decision not in ("APPROVE", "REJECT", "REFER"):
            decision = await loop.run_in_executor(
                None,
                lambda: input("Decision (APPROVE / REJECT / REFER): ").strip().upper(),
            )
            if decision not in ("APPROVE", "REJECT", "REFER"):
                print("Please enter APPROVE, REJECT, or REFER.")

        outcome = await submit_officer_decision(
            decision, USER_ID, session_id, session_service
        )
        print("\nOutcome:", outcome)
        print()


if __name__ == "__main__":
    asyncio.run(main())
