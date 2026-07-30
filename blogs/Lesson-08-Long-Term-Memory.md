# Lesson 8: Long-Term Memory

Lessons 6a and 6b gave an agent memory within a single conversation. This lesson extends that past a single conversation entirely, to a relationship manager assistant that needs to recall what a client told it in a previous, completely separate session.

## The problem we're solving

A private wealth management relationship manager builds a real relationship with a client over many separate conversations: a call today, a follow-up next week, a portfolio review next month. If a client mentioned three weeks ago that they want strictly conservative, low-risk investments and have a strong interest in ESG (environmental, social, and governance) funds, a good relationship manager doesn't make them repeat that on every call. An AI assistant standing in for part of that relationship needs the same continuity, and session state can't provide it — state is scoped to one conversation and gone once that session ends.

## Session state versus memory

Session state, from Lessons 6a and 6b, lives inside one `Session` object. It accumulates during a conversation and is readable for as long as that session is open. Once the process ends, or once you create a fresh session with a new `session_id`, that state is gone. `InMemorySessionService` is exactly what the name says — pure in-memory storage that vanishes the moment the process exits. If you want sessions to survive across restarts, you'd use `DatabaseSessionService`, which backs session storage with a real database. But either way, state is scoped to a session: a brand new session always starts empty.

Memory is a different layer entirely. It's a searchable archive that spans *across* separate sessions for the same user, built specifically so information from an old conversation can resurface in a new one. Two operations drive it:

- `add_session_to_memory` stores a session's conversation content into the archive.
- `search_memory` takes a text query and returns relevant content from everything stored for that user, regardless of which session it came from.

> 🎗️**A helpful way to visualise this:** 
>
> Think of a **Session** as equivalent to one chat conversation in Claude.ai or ChatGPT — it has a beginning, a history of everything said back and forth, and when you start a new chat, that history isn't automatically visible. Memory, in ADK's sense, is the equivalent of ChatGPT's memory panel — it spans *across* many separate chats, surfacing things the user told it previously without them having to repeat themselves. The difference is that in ADK, you control exactly what gets remembered, when it gets saved, and how it gets searched, rather than leaving those decisions to the platform.


ADK ships a ready-to-use tool called `load_memory` that wraps `search_memory` as something an agent can call mid-conversation, the same way it calls any other function tool. Unlike `google_search` from Lesson 4, `load_memory` is not a Gemini-only built-in — it's a plain `FunctionTool` that works identically on Claude or any other model.

**How we'll simulate long-term memory in this lesson:** 

To prove that memory works across sessions, we need to run two completely separate conversations with the same agent — one where the client states their preferences, and a second one where the agent recalls them without being told again. In `main.py`, we do this by creating two distinct `Session` objects, one after the other, with different `session_id`s. Each session starts with an empty conversation history, exactly as if it were a real new conversation days later. The critical point is that both sessions share the same `InMemoryMemoryService` instance, which lives for the entire duration of the script. When Session 1's `after_agent_callback` saves to memory, and Session 2's `load_memory` tool searches it, they're both talking to the same object.

If you tried to test this with `adk run` or `adk web` instead, you'd need to close and reopen the tool between the two sessions to simulate a fresh conversation — but doing so kills the process, which wipes `InMemoryMemoryService` entirely. You'd end up testing an agent with no memory at all. So that approach is not advisable for this example!

## Step 1: Build the relationship manager agent

Create the folder structure:

```bash
mkdir -p agents/lesson08_long_term_memory/relationship_manager
```

Create `agents/lesson08_long_term_memory/relationship_manager/agent.py`:

```python
"""Lesson 8: Long-Term Memory.

A relationship manager assistant for a wealth management desk. It
saves every turn to long-term memory automatically via an
after_agent_callback, and searches that memory before answering
investment questions so it can recall client preferences stated in
previous, entirely separate sessions.
"""

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import load_memory

from common.model_config import get_model


async def save_to_memory(callback_context: CallbackContext) -> None:
    """Saves this turn to long-term memory after every agent response.

    Fires automatically after every turn via after_agent_callback.
    Requires a memory_service to be wired into the Runner in main.py;
    without one, this raises a ValueError at runtime.

    Args:
        callback_context: Injected automatically by ADK. Must be named
            exactly "callback_context" — ADK enforces this.
    """
    await callback_context.add_session_to_memory()


AGENT_INSTRUCTION = (
    "You are a relationship manager assistant for a private wealth "
    "management desk. Before answering any investment-related question, "
    "use the load_memory tool to check whether this client has stated "
    "relevant preferences in past conversations, such as risk tolerance, "
    "sector interests, or exclusions like fossil fuels or tobacco. "
    "If memory returns relevant context, use it to personalise your "
    "response without asking the client to repeat themselves. If memory "
    "returns nothing relevant, answer using only what the client has "
    "said in this conversation. Never fabricate preferences the client "
    "did not state. Always clarify you are providing general information, "
    "not personalised investment advice, which requires a licensed advisor."
)

root_agent = Agent(
    name="relationship_manager_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description=(
        "Wealth management RM assistant that recalls client preferences "
        "across separate conversations using long-term memory."
    ),
    tools=[load_memory],
    after_agent_callback=save_to_memory,
)
```

Create `agents/lesson08_long_term_memory/relationship_manager/__init__.py`:

```python
from . import agent
```

Two things in this agent are new. `load_memory` in `tools` is ADK's built-in memory search tool — when the model calls it, it runs `search_memory` against whatever `MemoryService` is attached to the `Runner` and returns relevant past content. The instruction explicitly tells the agent when to reach for it, since models won't reliably check memory on their own just because the tool is available.

`after_agent_callback=save_to_memory` wires the memory-saving callback. `callback_context.add_session_to_memory()` hands the current session's events to the `MemoryService` after every single turn. We save after every turn rather than waiting for a "session end" signal, because there's no clean, detectable end point in a conversational session — and saving immediately means a client's preferences become recallable almost at once rather than only after some explicit close step.

## Step 2: Write main.py

The key design in this `main.py` is that both sessions share the same `InMemoryMemoryService` instance. Session 1 runs, saves to memory via the callback, then Session 2 starts fresh — same process, same memory service object — and the agent can recall what was said in Session 1 even though Session 2's own history is empty.

Create `agents/lesson08_long_term_memory/main.py`:

```python
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
```

The structure here is worth understanding before you run it. `session_service` and `memory_service` are created once at the top of `main()` and passed to the `Runner`. Every call to `run_session` or `interactive_session` creates a *new* `Session` via `session_service.create_session(...)`, which starts with an empty history. But the `memory_service` object is the same Python instance throughout, so when Session 1's `after_agent_callback` calls `add_session_to_memory()`, that content lands in the same `InMemoryMemoryService` that Session 2's `load_memory` tool will search. This is the critical difference from closing and reopening the process: the memory service never gets garbage collected between the two sessions.

`run_session` takes a list of pre-set prompts and plays them through automatically — useful for the demo's first session where we want reproducible, scripted input. `interactive_session` switches to a real `input()` loop driven by `run_in_executor`, the non-blocking pattern from Lesson 7b, so Session 2 is fully interactive and you can type whatever you like to test recall.

## Step 3: Run it

```bash
uv run agents/lesson08_long_term_memory/main.py
```

The script runs Session 1 automatically with two scripted prompts, printing what the agent says in response. After Session 1 completes, it pauses and asks you to press Enter before starting Session 2.

In Session 2, try a question that doesn't repeat any of what you said in Session 1:

```
What kind of portfolio would suit me this quarter?
```

You should see the agent call `load_memory` with a query like "investment preferences risk tolerance ESG", retrieve the content from Session 1, and produce a response shaped by those preferences, steering toward conservative, ESG-aligned options, even though Session 2's own conversation history is completely empty. That cross-session recall is the proof this lesson is after.

Try a few more questions in Session 2 to confirm the recall is consistent. Type `done` when finished.

## What production memory looks like

`InMemoryMemoryService` uses simple keyword matching and resets on every process exit. For a real deployed application, you'd swap it for a persistent backend at the `Runner` level:

```python
# Production example — everything else stays identical
from google.adk.memory.vertex_ai_rag_memory_service import VertexAiRagMemoryService

memory_service = VertexAiRagMemoryService(
    rag_corpus="projects/YOUR_PROJECT/locations/us-central1/ragCorpora/YOUR_CORPUS"
)
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
    memory_service=memory_service,
)
```

The agent code, the `load_memory` tool, and the `add_session_to_memory` callback are untouched. Only the service implementation changes.

## If you're coming from LangChain or LangGraph

This is conceptually close to a RAG (retrieval-augmented generation) setup in LangChain: store conversation content somewhere searchable, then retrieve relevant pieces back into context on a later query. The difference is how much of that ADK handles for you. In LangChain you'd typically choose and wire up a vector store yourself, write the retrieval query logic, and decide when to trigger storage. ADK's `MemoryService` interface standardises that pattern into two operations behind a common interface, so swapping `InMemoryMemoryService` for a production vector-search-backed implementation is a one-line configuration change rather than a rewrite of any agent logic.

## In this lesson

We gave an agent memory that survives past a single conversation. The relationship manager assistant automatically saves what a client tells it via `after_agent_callback`, and can recall that information in a completely separate, fresh session using the `load_memory` tool. We also saw exactly why this lesson needed `main.py` rather than `adk run`/`adk web`: `InMemoryMemoryService` lives for the life of the process, and keeping two sessions inside one `main()` call is what keeps the memory service alive between them.

## In the next lesson

Lesson 9 covers Production Serving — how to wrap the agent we've built behind a FastAPI endpoint so external systems can call it, using the `Runner` and `SessionService` patterns from Lesson 6a, this time with the `MemoryService` also wired in.
