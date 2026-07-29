# Lesson 6b: Sessions & State — the Tool's View

The previous lesson showed an agent reading pre-seeded state from a session: context that existed before the conversation began, handed in by the application, and read back through instruction templating. What it deliberately didn't show was an agent writing new state during a conversation. That's this lesson.

## The problem we're solving

Opening a new bank account in most countries requires a process called KYC, which stands for Know Your Customer. Before a bank can activate an account, it must collect and verify a specific set of details about the customer: their full name, date of birth, residential address, the type and number of a government-issued ID, employment status, and their source of funds. These aren't optional, they're a regulatory requirement, and the bank needs all seven before the application can move forward.

In a traditional flow, a branch officer or call centre agent works through these fields one at a time in a conversation with the customer. The customer doesn't arrive with everything ready to paste into a form, they answer one question, then the next, sometimes going off to find a document and coming back, across several turns of back-and-forth. The officer needs to track what's already been given and what's still missing, without losing anything already said and without re-asking for something the customer already provided.

An AI agent can handle exactly this kind of guided, multi-turn collection. But there's a real challenge: the model itself doesn't retain information between turns the way a person does. If a customer gives their name in turn one and their address in turn three, the agent needs a reliable way to remember that the name is already collected, so it doesn't ask for it again. That's where session state comes in, and specifically, where writing to session state from inside a tool becomes the right design.

## The write mechanism: ToolContext

The write mechanism in this lesson is something you already know: a tool. In Lesson 3 you wrote tools that do a calculation and return the result as a dict. Here, a tool does something slightly different: alongside returning its result, it also writes directly into the session's state dictionary through a special parameter called `ToolContext`. When ADK calls your tool function, it automatically injects this object if you declare a parameter typed as `ToolContext`. Through it, your tool can read from and write to the session's state, just like a regular Python dictionary. Whatever the tool writes persists in the session for the rest of the conversation, and the agent's instruction can read it back on every subsequent turn using `{key_name}` placeholders, the same templating you saw in Lesson 6a.

## Step 1: Write the KYC tracking tool

Create the folder:

```bash
mkdir -p agents/lesson06b_sessions_and_state/kyc_onboarding
```

Create `agents/lesson06b_sessions_and_state/kyc_onboarding/tools.py`:

```python
"""Lesson 6b: Sessions & State, the tool's view.

KYC field tracking tool. Writes collected fields and a status
summary into session state on every call, so the agent's instruction
can read current progress back on the very next turn.
"""

from google.adk.tools import ToolContext

REQUIRED_KYC_FIELDS = [
    "full_name",
    "date_of_birth",
    "residential_address",
    "id_type",
    "id_number",
    "employment_status",
    "source_of_funds",
]


def record_kyc_detail(
    tool_context: ToolContext,
    field_name: str,
    field_value: str,
) -> dict:
    """Records one KYC field for the customer currently being onboarded.

    Args:
        tool_context: Injected automatically by ADK; gives access to
            the current session's state.
        field_name: Which KYC field this is. Must be one of: full_name,
            date_of_birth, residential_address, id_type, id_number,
            employment_status, source_of_funds.
        field_value: The value the customer provided for this field.

    Returns:
        A dict confirming what was recorded, what has been collected so
        far, and which required fields are still missing.
    """
    if field_name not in REQUIRED_KYC_FIELDS:
        return {
            "error": (
                f"Unknown field '{field_name}'. Valid fields are: "
                f"{', '.join(REQUIRED_KYC_FIELDS)}"
            )
        }

    kyc_data = tool_context.state.get("kyc_data", {})
    kyc_data[field_name] = field_value
    tool_context.state["kyc_data"] = kyc_data

    missing = [f for f in REQUIRED_KYC_FIELDS if f not in kyc_data]
    is_complete = not missing
    tool_context.state["kyc_status"] = (
        "All required KYC fields collected."
        if is_complete
        else f"Still missing: {', '.join(missing)}"
    )

    return {
        "recorded_field": field_name,
        "kyc_data_so_far": kyc_data,
        "missing_fields": missing,
        "is_complete": is_complete,
    }
```

A few things in this function are worth calling out. `tool_context.state.get("kyc_data", {})` reads whatever's already been collected, defaulting to an empty dict on the first call, then adds the new field and writes the whole dict back as `tool_context.state["kyc_data"] = kyc_data`. That reassignment matters: always write the complete value back to the key after modifying it, rather than assuming an in-place mutation on a nested object will persist. State changes are tracked as explicit key assignments on `tool_context.state`, not as deep mutations inside values you've already read out.

The function writes two keys: `kyc_data`, the full dictionary of everything collected so far, and `kyc_status`, a short human-readable summary of what's still missing. The agent's instruction is about to read `kyc_status` back directly through templating. Having a short string for this, rather than forcing the model to interpret the full `kyc_data` dict each time, keeps the instruction lightweight and the model's reasoning clear.

## Step 2: Build the agent

Create `agents/lesson06b_sessions_and_state/kyc_onboarding/agent.py`:

```python
"""Lesson 6b: Sessions & State, the tool's view.

A KYC onboarding agent for a retail bank's digital account-opening
flow. Collects required customer details one or two at a time across
a multi-turn conversation, tracking progress via tool-driven session
state rather than relying on the model to remember what it has asked.
"""

from google.adk.agents import Agent

from common.model_config import get_model
from .tools import record_kyc_detail

AGENT_INSTRUCTION = (
    "You are a KYC (Know Your Customer) onboarding assistant for a "
    "retail bank opening a new account. You need to collect these "
    "fields from the customer, one or two at a time in natural "
    "conversation: full_name, date_of_birth, residential_address, "
    "id_type, id_number, employment_status, source_of_funds. "
    "Current progress: {kyc_status?}. "
    "Whenever the customer gives you a value for one of these fields, "
    "call record_kyc_detail immediately to save it, then ask for the "
    "next missing field. Do not re-ask for a field that the current "
    "progress already shows as collected. Once all fields are "
    "collected, thank the customer and confirm their application is "
    "ready for review; do not make any approval decision yourself."
)

root_agent = Agent(
    name="kyc_onboarding_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description=(
        "Collects KYC details from a customer opening a new bank "
        "account, tracking progress across a multi-turn conversation."
    ),
    tools=[record_kyc_detail],
)
```

Create `agents/lesson06b_sessions_and_state/kyc_onboarding/__init__.py`:

```python
from . import agent
```

The instruction uses `{kyc_status?}` with a trailing `?`, and this is a good moment to explain exactly why. In Lesson 6a, all the placeholder keys in the instruction were guaranteed to exist before the first turn, because `main.py` had seeded them into the session at creation time. Here, `kyc_status` is different: it gets written into state by the tool, and the tool only fires when the customer actually provides a field value. A customer's opening message might be a general question like "what do I need to provide?" rather than a direct answer, so on that very first turn, before any tool has run, `kyc_status` simply doesn't exist in session state yet. If you reference a missing key without any marker, ADK raises an error rather than silently substituting an empty string. The trailing `?` tells ADK to treat this key as optional and substitute an empty string when it isn't found, rather than failing. The rule is simple: any state key that might not be present on the very first turn of a conversation needs the `?`.

The instruction also explicitly tells the model to call the tool immediately when the customer gives a field value, and not to re-ask for fields the progress string already shows as collected. Both of these are necessary: without the first, the model might answer conversationally without saving anything; without the second, it might ask for a customer's name twice without realising it already has the answer, since the model itself doesn't remember state, the session does.

## Step 3: Write main.py

Create `agents/lesson06b_sessions_and_state/main.py`:

```python
"""Lesson 6b: Sessions & State, the tool's view.

Drives the KYC onboarding agent through a console chat loop.
After every turn, the current session state is printed so you can
watch tool-driven state accumulate in real time as the conversation
progresses.

Run with:
    uv run agents/lesson06b_sessions_and_state/main.py
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from kyc_onboarding.agent import root_agent

APP_NAME = "kyc_onboarding_app"
USER_ID = "demo_user"


async def main() -> None:
    """Runs a console KYC onboarding conversation, printing state after every turn."""
    session_service = InMemorySessionService()

    # No pre-seeded state this time: the session starts empty and the
    # tool builds it up as the customer provides each field.
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
    )

    print("KYC Onboarding Assistant (type 'exit' to quit)\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
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

        # Fetch the latest session state and print it after every turn.
        # This is the key difference from what adk web/run showed you:
        # you can inspect the exact state of the session at any point
        # in the conversation, not just infer it from what the agent says.
        updated_session = await session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session.id
        )
        print(f"[session state] {updated_session.state}\n")


if __name__ == "__main__":
    asyncio.run(main())
```

Notice one deliberate addition in this `main.py` that wasn't in Lesson 6a's: after every turn, we call `session_service.get_session(...)` and print `updated_session.state`. This is one of the things that writing your own driving loop makes possible: you can reach into the session at any point and inspect exactly what's in it, not just infer it from the agent's conversational output. Here it serves as a live view of the tool doing its job, you'll see `kyc_data` and `kyc_status` grow with each field the customer provides, and nothing change on turns where they give the agent something that doesn't map to a KYC field.

## Step 4: Run it

```bash
uv run agents/lesson06b_sessions_and_state/main.py
```

Have a natural multi-turn conversation rather than giving everything at once:

```
Hi, I'd like to open a new account
```

The agent should introduce the KYC process and ask for the first field. Then provide details one or two at a time:

```
My name is Priya Sharma and I was born on 14 March 1990
```

After the agent responds, you'll see the `[session state]` line print below it, showing `kyc_data` and `kyc_status` already updated to reflect the two fields just collected. Keep going, providing your address, ID details, employment status, and source of funds across several more turns. Watch the state grow with every field you provide, and stay unchanged on turns where you ask a question rather than giving a value. On the final turn, when all seven fields are collected, `kyc_status` in the state should show "All required KYC fields collected." and the agent should confirm the application is ready for review.

> **NOTE:** If you want to test this with `adk run` or `adk web` for quick iteration rather than the full console loop, point them at the agent's subfolder directly: `adk run agents/lesson06b_sessions_and_state/kyc_onboarding` or `adk web agents/lesson06b_sessions_and_state`. The state inspector panel in `adk web` gives you the same live view of `kyc_data` and `kyc_status` that our `print` statement provides here.

## How this differs from Lesson 6a

Put the two lessons side by side and the contrast is clean. In Lesson 6a, state was external, created by the application before the agent ran, and flowed only inward, the agent read it but never changed it. In this lesson, state is internal, starts empty, and grows during the conversation as the tool writes to it. Neither is more "correct" than the other; they're two different patterns for two different situations. Real applications use both: a production KYC flow might pre-seed the session with whatever the bank already knows about the customer (from login, from an existing account), and then let the agent fill in the rest through tool calls as the conversation progresses.

## If you're coming from LangChain or LangGraph

The `tool_context.state` pattern maps closely to how LangGraph state graphs work: every node, including ones that wrap tool calls, can read and write the shared state object that flows through the graph. ADK's version is slightly different in that you're not explicitly passing state through a graph structure, it's transparently shared across whatever the runner is doing on any given turn, but the developer experience, write a typed function that reads from and writes to a shared dictionary, is familiar.

## In this lesson

We gave an agent the ability to modify its own session state during a conversation, using a tool. The KYC onboarding agent now tracks exactly which required fields have been collected and which are still missing, field by field, across as many turns as the conversation takes. The session carries that progress reliably between every turn, and the agent's own instruction reads it back automatically, so it never re-asks for something it already has.

## In the next lesson

With session state fully in our hands, we turn to a different kind of control: _callbacks_. ADK lets you attach hook functions that fire automatically at six specific points in every turn: before and after the agent runs, before and after the model is called, and before and after each tool executes. Callbacks are what let you add cross-cutting behaviour, logging, guardrails, state updates, custom routing, without touching the agent's core logic. The next lesson introduces the callback mechanism properly before we start building with each type.
