"""Shared Runner utility for querying any ADK agent programmatically.

Used from Lesson 6a onward as the standard way to run an agent outside
of adk run / adk web. The optional memory_service parameter was added
in Lesson 9 to support agents that use long-term memory.
"""

from typing import Optional

from google.adk.agents import BaseAgent
from google.adk.memory.base_memory_service import BaseMemoryService
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService
from google.genai import types


async def get_or_create_session(
    session_service: BaseSessionService,
    app_name: str,
    user_id: str,
    session_id: str,
):
    """Fetches an existing session, or creates a new one if it doesn't exist yet.

    Args:
        session_service: The session service backing this conversation.
        app_name: A name identifying this application to the session service.
        user_id: Identifies the end user for this conversation.
        session_id: Identifies this specific conversation.

    Returns:
        The existing or newly created Session object.
    """
    session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    if session is None:
        session = await session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
    return session


async def run_agent_query(
    agent: BaseAgent,
    app_name: str,
    user_id: str,
    session_id: str,
    query: str,
    session_service: BaseSessionService,
    memory_service: Optional[BaseMemoryService] = None,
) -> str:
    """Sends one query to an agent and returns its final text response.

    Args:
        agent: The ADK agent to run.
        app_name: A name identifying this application to the session service.
        user_id: Identifies the end user for this conversation.
        session_id: Identifies this specific conversation.
        query: The user's message text.
        session_service: The session service backing this conversation.
            Passed in rather than created here so callers can reuse the
            same service, and therefore the same session state, across
            multiple calls.
        memory_service: Optional. Pass this when the agent uses load_memory
            or after_agent_callback to save to long-term memory. Omit it
            for agents that don't use memory at all.

    Returns:
        The agent's final response text for this turn.
    """
    session = await get_or_create_session(session_service, app_name, user_id, session_id)

    runner = Runner(
        app_name=app_name,
        agent=agent,
        session_service=session_service,
        memory_service=memory_service,
    )

    user_message = types.Content(role="user", parts=[types.Part(text=query)])

    final_response_text = "(no response received)"
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response_text = "".join(
                part.text for part in event.content.parts if part.text
            )

    return final_response_text