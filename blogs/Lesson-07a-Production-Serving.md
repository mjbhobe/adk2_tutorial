# Lesson 7a: From Testing to Production — Runner, SessionService, and Serving Your Agent

Every lesson so far has run through `adk run` or `adk web`. Both are genuinely good tools, and we're going to keep using them for quick testing throughout the rest of this series. But neither is how an agent actually runs once it's serving real users, and this lesson is entirely about that gap: what `adk run`/`adk web` are quietly doing for you, why that stops being appropriate in production, and how to build the same thing yourself, deliberately, so you understand exactly what's underneath it.

This is a deeper, more mechanical lesson than usual, and on purpose. Lesson 8 starts building real multi-agent pipelines, and that lesson deserves your full attention on multi-agent concepts, not on also learning how a Runner works for the first time. So we're isolating that concept here, building it once, carefully, and reusing it for the rest of the series from Lesson 8 onward.

## Why adk run and adk web aren't how you'd actually run this

Think about what `adk run` and `adk web` are doing every time you use them. They pick a session service (local SQLite by default, as we corrected back in Lesson 6). They construct something called a `Runner` behind the scenes. They manage an event loop that feeds your typed message in and streams the agent's response back out. They handle multiple turns, tool calls, and callbacks, all invisibly. That's exactly why they've been so convenient through six lessons: you've never had to think about any of that machinery.

None of it is designed to serve real traffic, though. `adk run` is a single interactive terminal session, one person, one conversation, blocking on keyboard input between turns. `adk web` is a local development server meant for you to poke at an agent in a browser while you're building it. Neither is built to sit behind a load balancer, handle many users' conversations concurrently, or be called by some other application that isn't a human typing into a terminal.

And that last part is the real shape of production. A relationship manager assistant like the one from Lesson 7 doesn't exist so that a developer can chat with it in a terminal. It exists so that some other system, a bank's customer portal, a mobile app, an internal case-management tool, can call it, send it a message, and get a response back, as part of a much larger application most of whose code has nothing to do with ADK at all. That calling system needs a stable interface to call: an API endpoint. It sends a request, it gets a response, it doesn't know or care that a `Runner` and a `SessionService` exist inside.

## What a Runner actually does

A `Runner` is the piece of ADK that actually executes one turn of a conversation with an agent. When you hand it a user's message, a session, and an agent, it's responsible for the full round trip: sending the conversation so far to the model, handling any tool calls the model requests (running your Python functions, feeding results back), applying any callbacks you've registered (like Lesson 7's memory-saving callback), and doing all of that potentially several times in a row within a single turn, since a model might call a tool, look at the result, and decide to call another tool before it's ready to give you a final answer.

All of that happens as a stream of `Event` objects. Every intermediate step, a tool being called, a tool's result coming back, a partial or final piece of text from the model, arrives as one `Event`. The `Runner` doesn't just hand you back a single string at the end; it hands you an async stream of these events as they happen, and it's your job (or `adk run`/`adk web`'s job, which you've never had to look at) to consume that stream and decide what to do with it, typically: ignore the intermediate events and grab the text from whichever event represents the final, complete response.

A `SessionService` is what a `Runner` reads from and writes to as it works: the conversation history, and the state dictionary from Lesson 6. Critically, the `Runner` doesn't own this data itself, it's handed a session service to use. That's a deliberate design: the same `Runner` code can run against an in-memory session service for quick local testing, or a persistent, database-backed one for production, without the `Runner`'s own logic changing at all.

## Step 1: Build a reusable Runner helper

We're writing this once, in a shared location, since every lesson from here on will use exactly this pattern.

Add the dependencies we'll need for this lesson:

```bash
uv add fastapi uvicorn streamlit requests
```

Create `agents/common/runner_utils.py`:

```python
"""Shared Runner utility for querying any ADK agent programmatically.

Used from Lesson 7a onward as the standard way to run an agent outside
of adk run / adk web, e.g. behind an API endpoint or from a script.
"""

from google.adk.agents import BaseAgent
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
) -> str:
    """Sends one query to an agent and returns its final text response.

    Args:
        agent: The ADK agent to run.
        app_name: A name identifying this application to the session service.
        user_id: Identifies the end user for this conversation.
        session_id: Identifies this specific conversation.
        query: The user's message text.
        session_service: The session service backing this conversation.
            Passed in rather than created here, so callers can reuse the
            same service, and therefore the same session state, across
            multiple calls.

    Returns:
        The agent's final response text for this turn.
    """
    await get_or_create_session(session_service, app_name, user_id, session_id)

    runner = Runner(
        app_name=app_name,
        agent=agent,
        session_service=session_service,
    )

    user_message = types.Content(role="user", parts=[types.Part(text=query)])

    final_response_text = "(no response received)"
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response_text = "".join(
                part.text for part in event.content.parts if part.text
            )

    return final_response_text
```

Walk through `run_agent_query` slowly, since every line here is doing something you've never had to write before. `get_or_create_session` exists because `Runner.run_async` expects a session to already exist, it won't silently create one for you the way `adk run`/`adk web` do behind the scenes. We check for an existing session first, since we want repeated calls with the same `session_id` to continue the same conversation, and only create a new one if this is genuinely the first message.

Constructing `Runner(app_name=..., agent=..., session_service=...)` is the point where you're building, by hand, exactly the object `adk run` and `adk web` have been quietly building for you every single lesson. Note that we're building a fresh `Runner` on every call here, that's fine, a `Runner` is a lightweight coordinator, not something expensive to create; what actually needs to persist across calls is the `session_service`, which is why it's passed in rather than created inside this function.

The `async for event in runner.run_async(...)` loop is the event stream we described above, made concrete. `runner.run_async` doesn't return a value, it's an async generator, so every event, every tool call, every partial output, every callback firing, streams through this loop one at a time. `event.is_final_response()` is a helper ADK provides specifically so you don't have to reimplement the logic for "is this the actual, complete answer, or just an intermediate step" yourself; it returns `True` only once the model has produced a complete response with no pending tool calls. When that happens, we pull the text out of `event.content.parts` and that becomes our return value.

## Step 2: Build the API server

This is the piece that turns `run_agent_query` into something another application can actually call.

Create `main.py` at your project root:

```python
"""FastAPI server exposing the Lesson 7 relationship manager agent.

This is the production-shaped way to run an ADK agent: as a long-lived
API server, called by other systems (a web app, a console client, a
mobile app), rather than through adk run's interactive CLI loop or
adk web's browser UI, both of which are testing tools, not serving
infrastructure.

Run with:
    uv run main.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "agents"))

from fastapi import FastAPI
from google.adk.sessions import InMemorySessionService
from pydantic import BaseModel

from common.runner_utils import run_agent_query
from lesson07_relationship_manager.agent import root_agent

APP_NAME = "wealth_management_app"

# One shared session service for the life of this process. Every
# request reads and writes through this same instance, which is what
# makes multi-turn conversations and cross-session memory recall work
# at all; a fresh instance per request would reset everything every
# single time a request came in.
session_service = InMemorySessionService()


class ChatRequest(BaseModel):
    """The shape of an incoming request to /chat."""

    user_id: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    """The shape of a response from /chat."""

    response: str


app = FastAPI(title="Relationship Manager Agent API")


@app.get("/health")
async def health() -> dict:
    """Simple liveness check, useful once this is actually deployed."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Sends one message to the relationship manager agent and returns its reply."""
    response_text = await run_agent_query(
        agent=root_agent,
        app_name=APP_NAME,
        user_id=request.user_id,
        session_id=request.session_id,
        query=request.message,
        session_service=session_service,
    )
    return ChatResponse(response=response_text)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)
```

A few things worth being precise about here. `session_service = InMemorySessionService()` is created once, at module load time, as a variable the whole file shares, not inside the `/chat` endpoint function. This matters enormously: if we created a new `InMemorySessionService()` inside `chat()` on every request, every single message would start a brand new, empty session, and nothing from Lesson 6 or Lesson 7, state tracking or memory recall, would work at all. One long-running process, one shared session service, is what makes continuity possible; this is also exactly why we're launching this as a persistent server with `uv run main.py`, rather than something that starts fresh per request.

The `/chat` endpoint itself is thin on purpose: parse the incoming request into a typed `ChatRequest`, hand it straight to `run_agent_query`, wrap the result in a `ChatResponse`. All the actual complexity, the `Runner`, the event loop, session handling, lives in `runner_utils.py` where we can reuse it, not duplicated inside every endpoint we might add later.

> **NOTE:** ADK actually ships its own shortcut for exactly this, an `adk api_server` CLI command (and an underlying `get_fast_api_app()` helper) that stands up a FastAPI server for an agent directory automatically, with session handling wired in for you, similar to how `adk web` wires things up for its browser UI. We're deliberately not using it here. The whole point of this lesson is to see what a `Runner`, a `SessionService`, and an event loop actually are, and reaching for another ADK convenience layer would just swap one kind of magic for another without showing you what's inside it. Once you understand this lesson, `adk api_server` is a perfectly reasonable shortcut to reach for in a real project, and we'll mention it again when we get to deployment in Lesson 14.

Here's the architecture this gives us, end to end:

![Diagram showing two client types, a Streamlit web UI and a console client, sending HTTP POST requests to a FastAPI server (main.py), which uses a Runner and shared SessionService to drive the relationship_manager_agent, which in turn calls Claude Haiku via the Anthropic API.](./production-serving-architecture.png)

## Step 3: Run the API server

From your project root:

```bash
uv run main.py
```

You should see Uvicorn's startup log, ending with something like `Uvicorn running on http://127.0.0.1:8080`. Leave this running, this is your agent's API, and everything else in this lesson talks to it over HTTP. Open `http://127.0.0.1:8080/docs` in a browser; FastAPI generates an interactive API explorer automatically, and you can try the `/chat` endpoint directly from there if you want to see a raw request and response before we build any client.

## Step 4: Build a dummy web front-end with Streamlit

In production, something like this would be a real feature inside your bank's existing customer portal or advisor toolkit, not a new standalone app. We're building a deliberately minimal stand-in, just enough to prove the API works from a real web UI, without pretending to teach you production frontend development in the middle of an ADK series.

Create `streamlit_app.py` at your project root:

```python
"""Dummy web front-end for the relationship manager agent.

Stands in for a real production system, such as an existing wealth
management portal, that would call our agent's API rather than
embedding ADK directly. Run this alongside main.py, not instead of it.

Run with:
    streamlit run streamlit_app.py
"""

import uuid

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8080/chat"

st.set_page_config(page_title="Wealth Management Assistant", page_icon="💬")
st.title("Wealth Management Assistant")
st.caption(
    "This is a dummy front-end standing in for a real banking portal. "
    "It knows nothing about ADK; it only talks to our agent's API."
)

if "user_id" not in st.session_state:
    st.session_state.user_id = f"streamlit-user-{uuid.uuid4().hex[:8]}"
if "session_id" not in st.session_state:
    st.session_state.session_id = f"streamlit-session-{uuid.uuid4().hex[:8]}"
if "messages" not in st.session_state:
    st.session_state.messages = []

for role, text in st.session_state.messages:
    with st.chat_message(role):
        st.write(text)

user_input = st.chat_input("Ask about your portfolio...")

if user_input:
    st.session_state.messages.append(("user", user_input))
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = requests.post(
                API_URL,
                json={
                    "user_id": st.session_state.user_id,
                    "session_id": st.session_state.session_id,
                    "message": user_input,
                },
                timeout=60,
            )
            response.raise_for_status()
            reply_text = response.json()["response"]
        st.write(reply_text)

    st.session_state.messages.append(("assistant", reply_text))
```

Worth being careful about here: `st.session_state` is Streamlit's own concept, a dictionary that persists across reruns of the script within one browser tab, and it is completely unrelated to ADK's `SessionService`. They share a name by coincidence, not by design. We're using Streamlit's session state purely to remember the `user_id` and `session_id` strings for this browser tab, generated once with `uuid.uuid4()` the first time the page loads, so that every message sent from this tab consistently reaches the same ADK session on the server side. The actual conversation history and state, the thing that makes the agent remember what you told it, lives entirely on the server, inside `main.py`'s `InMemorySessionService`, not in Streamlit at all.

In a new terminal, with `main.py` still running in the first one:

```bash
uv run streamlit run streamlit_app.py
```

Streamlit will open a browser tab automatically. Chat with the agent the way you did in Lesson 7's `adk web` testing, tell it your investment preferences, then ask it something later that requires recalling them. It should behave identically to what you saw in Lesson 7, because underneath, it's the exact same agent, the exact same `load_memory` tool, and the exact same memory-saving callback; only the surface you're talking through has changed.

## Step 5: Build a console client

This one exists purely to make a point: the API doesn't care what's calling it. A browser-based UI and a bare command-line script are equally valid clients, as far as `main.py` is concerned.

Create `console_client.py` at your project root:

```python
"""Console client for the relationship manager agent's API.

A second, minimal illustration of calling the same API endpoint the
Streamlit app uses, this time from a plain command-line script rather
than a web UI. Run this alongside main.py.

Run with:
    uv run console_client.py
"""

import uuid

import requests

API_URL = "http://127.0.0.1:8080/chat"


def main() -> None:
    """Runs a simple command-line chat loop against the agent's API."""
    user_id = f"console-user-{uuid.uuid4().hex[:8]}"
    session_id = f"console-session-{uuid.uuid4().hex[:8]}"

    print("Relationship Manager Assistant (console client)")
    print("Type 'exit' to quit.\n")

    while True:
        message = input("You: ").strip()
        if message.lower() in {"exit", "quit"}:
            break
        if not message:
            continue

        response = requests.post(
            API_URL,
            json={"user_id": user_id, "session_id": session_id, "message": message},
            timeout=60,
        )
        response.raise_for_status()
        print(f"Agent: {response.json()['response']}\n")


if __name__ == "__main__":
    main()
```

There's genuinely nothing ADK-specific in this file at all, and that's exactly the point worth sitting with. It's a plain `requests.post()` call to a URL. It could be written in any language that can make an HTTP request; it has no dependency on `google-adk`, no knowledge of agents, tools, or sessions. That's the real payoff of putting an API in front of your agent: everything downstream of `main.py` stops needing to know or care that ADK exists.

In a third terminal, with `main.py` still running:

```bash
uv run console_client.py
```

Have the same kind of conversation you just had in Streamlit, but note that this is a *different* `user_id`, so it won't share memory with your Streamlit conversation; each client here is simulating a different end user talking to the same running agent.

## If you're coming from LangChain or LangGraph

This pattern, a thin API layer wrapping an agent framework's own execution logic, isn't unique to ADK. LangChain and LangGraph applications reach production the same way, typically wrapped in FastAPI (or LangChain's own LangServe, when applicable) for exactly the same reason: the framework's own dev-mode entry points, LangGraph Studio included, aren't meant to be what a production caller talks to directly. If you've deployed a LangGraph app behind FastAPI before, `main.py` here should feel entirely familiar; the specific object being wrapped is different, ADK's `Runner` instead of a compiled LangGraph graph, but the shape of the solution, and the reason for it, is the same.

## Why this got a dedicated lesson

We could have folded this into Lesson 8 alongside multi-agent orchestration, but that would have meant learning two substantial new things at once: how agents actually get served outside ADK's own testing tools, and how multiple agents coordinate with each other. Splitting them means Lesson 8 can assume you already understand `Runner`, `SessionService`, and calling an agent over HTTP, and spend its entire attention on the actual multi-agent concepts instead.

## In this lesson

We stopped relying on `adk run` and `adk web`'s hidden scaffolding and built it ourselves: a `Runner` driving an agent's event loop, a shared `SessionService` keeping conversations continuous across separate HTTP requests, and a FastAPI server exposing all of it as a `/chat` endpoint. We then proved the API doesn't care who's calling it by building two completely different clients against it, a Streamlit web UI and a bare console script, both talking to the exact same running agent.

## In the next lesson

Lesson 8 puts this infrastructure to work on a genuinely multi-agent problem: a loan underwriting pipeline combining parallel risk checks with sequential decisioning, using `SequentialAgent`, `ParallelAgent`, and `LoopAgent`. We'll drive it through `main.py`, using the exact `Runner` and `SessionService` pattern from this lesson, so that lesson can focus entirely on how those agents coordinate with each other rather than on how any of them gets run.
