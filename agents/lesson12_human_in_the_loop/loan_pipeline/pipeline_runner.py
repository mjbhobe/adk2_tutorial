"""Lesson 12: Shared pipeline runner for the loan approval pipeline.

Both main.py (console) and api.py (web) call these exact two functions.
Neither front end talks to Runner or the session service directly,
which is what guarantees the HITL mechanism behaves identically no
matter which one is driving it.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from pathlib import Path

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService
from google.genai import types
from google.adk.artifacts import InMemoryArtifactService

from .agent import APP_NAME, outcome_app, review_app

TOOL_NAME = "request_officer_approval"
VALID_DECISIONS = ("APPROVE", "REJECT", "REFER")

artifact_service = InMemoryArtifactService()


async def _drive_run(
    runner: Runner, user_id: str, session_id: str, new_message: types.Content
) -> bool:
    """Consumes one run_async call, reporting whether it paused.

    Args:
        runner: The Runner driving this call.
        user_id: Identifies the applicant/officer's session owner.
        session_id: Identifies this specific application.
        new_message: The message to send.

    Returns:
        True if this run stopped at a long-running tool call.
    """
    paused = False
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=new_message
    ):
        if event.long_running_tool_ids:
            paused = True
    return paused


async def _save_artifact_to_disk(user_id: str, filename: str) -> str:
    """Pulls a saved artifact's bytes back out and writes them to a real file, so there's something to actually open."""
    part = await artifact_service.load_artifact(
        app_name=APP_NAME, user_id=user_id, filename=filename
    )
    output_dir = Path(__file__).resolve().parents[1] / "generated_documents"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / filename
    output_path.write_bytes(part.inline_data.data)
    return str(output_path)


async def submit_application(
    application_text: str,
    user_id: str,
    session_id: str,
    session_service: BaseSessionService,
) -> dict:
    """Runs a new application through credit check and risk scoring, up to the HITL checkpoint.

    Args:
        application_text: The applicant's details, as free-form text.
        user_id: Identifies this applicant's session owner.
        session_id: Identifies this specific application.
        session_service: Shared across calls, so state persists between
            this call and a later submit_officer_decision call.

    Returns:
        A dict with status "pending_officer_review" (the expected
        outcome) plus the credit and risk findings for display, or
        status "unexpected_completion" in the unlikely case nothing
        paused at all.
    """
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if session is None:
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

    runner = Runner(
        app=review_app,
        session_service=session_service,
        artifact_service=artifact_service,
    )
    paused = await _drive_run(
        runner,
        user_id,
        session_id,
        new_message=types.Content(
            role="user", parts=[types.Part(text=application_text)]
        ),
    )

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if paused:
        return {
            "status": "pending_officer_review",
            "credit_result": session.state.get("credit_result"),
            "risk_result": session.state.get("risk_result"),
        }
    return {"status": "unexpected_completion", "state": dict(session.state)}


async def submit_officer_decision(
    decision: str,
    user_id: str,
    session_id: str,
    session_service: BaseSessionService,
) -> dict:
    """Resumes a paused application with the officer's decision, then runs the outcome pipeline.

    Args:
        decision: One of "APPROVE", "REJECT", or "REFER".
        user_id: Must match the user_id submit_application was called with.
        session_id: Must match the session_id submit_application was called with.
        session_service: Must be the same instance used for submit_application.

    Returns:
        A dict with the officer's decision plus the outcome pipeline's
        results, disbursement details or a referral task, whichever
        applied.

    Raises:
        ValueError: If decision isn't one of the three valid values, or
            no pending application is found for this session.
    """
    decision = decision.strip().upper()
    if decision not in VALID_DECISIONS:
        raise ValueError(f"decision must be one of {VALID_DECISIONS}, got {decision!r}")

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if session is None:
        raise ValueError(
            "No application found for this session. Call submit_application first."
        )

    # Find the pending officer-approval call to resume. It's the most
    # recent event carrying long_running_tool_ids.
    pending_call_id = None
    for event in reversed(session.events):
        if event.long_running_tool_ids:
            pending_call_id = next(iter(event.long_running_tool_ids))
            break
    if pending_call_id is None:
        raise ValueError("No pending officer approval found for this session.")

    # Write the decision to state directly, before resuming, rather
    # than trusting a resumed model turn to write it correctly.
    decision_event = Event(
        author="pipeline_runner",
        actions=EventActions(state_delta={"officer_decision": decision}),
    )
    await session_service.append_event(session, decision_event)

    # Resume review_pipeline. This completes hitl_agent's own turn.
    review_runner = Runner(
        app=review_app,
        session_service=session_service,
        artifact_service=artifact_service,
    )
    resume_message = types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id=pending_call_id,
                    name=TOOL_NAME,
                    response={"officer_decision": decision},
                )
            )
        ],
    )
    await _drive_run(review_runner, user_id, session_id, new_message=resume_message)

    # Then explicitly run the outcome pipeline. It doesn't run on its
    # own, resuming review_pipeline only advances hitl_agent.
    outcome_runner = Runner(
        app=outcome_app,
        session_service=session_service,
        artifact_service=artifact_service,
    )
    await _drive_run(
        outcome_runner,
        user_id,
        session_id,
        new_message=types.Content(
            role="user", parts=[types.Part(text="Officer decision recorded, proceed.")]
        ),
    )

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )

    disbursement_result = session.state.get("disbursement_result")
    local_pdf_path = None
    if disbursement_result:
        local_pdf_path = await _save_artifact_to_disk(
            user_id, disbursement_result["artifact_filename"]
        )

    return {
        "officer_decision": session.state.get("officer_decision"),
        "disbursement_result": disbursement_result,
        "referral_task": session.state.get("referral_task"),
        "local_pdf_path": local_pdf_path,
    }
