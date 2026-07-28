# Lesson 6: Sessions & State

Lesson 5 gave an agent a guaranteed output shape, but every example through Lesson 5 has shared a limitation: each question stood on its own. The agent had no memory of anything said earlier in the same conversation, beyond whatever the chat window happened to still show on screen. This lesson fixes that with two related ADK concepts: _sessions_, which represent an ongoing conversation, and _state_, the data an agent can read and write as that conversation progresses.

## The problem we're solving

Opening a new bank account requires KYC (Know Your Customer) verification: full name, date of birth, address, a government ID, employment status, source of funds etc., collected before an account can be approved. In a real onboarding flow, a customer doesn't hand over all of this in one message. They answer one or two questions, get asked for the next thing, answer again, over several back-and-forth turns, sometimes over several minutes as they go find a document.

An agent handling this in an ongoing conversation needs to track, across that entire back-and-forth, what's already been collected and what's still missing, so it never re-asks for a customer's name three times or loses track of their date of birth the moment they mention their address instead. That's a memory problem within a single conversation, and it's exactly what sessions and state exist to solve.

## Sessions and state, and how they fit together

A session represents one ongoing conversation between a user and an agent. Every message you send and every response you get back becomes part of that session's history. Behind the scenes, a `SessionService` is what actually creates, stores, and retrieves sessions, when you use `adk run` or `adk web`, ADK sets one up for you automatically for the length of that run, so you haven't had to think about it in any lesson so far. Every conversation you've had while testing Lessons 2 through 5 was already happening inside a session, you just weren't reading or writing anything from it yet.

State is the data attached to a session: a plain dictionary your agent can read from and write to as the conversation progresses. This is different from the conversation history itself (the actual messages exchanged); state is a separate place for your agent to keep track of facts, like "the fields collected so far", that it needs across turns.

Two ways to touch state matter for this lesson. First, tools can read and write it directly, through `tool_context.state`, which behaves like a regular Python dict. Second, an agent's instruction text can reference a state value directly using `{key_name}` inside the instruction string, and ADK substitutes the current value in before every single turn, automatically. That second mechanism is what lets an agent's own system prompt stay aware of what's already been collected, without you writing any extra code to feed it back in.

## Step 1: Write the KYC-tracking tool

Create the folder:

```bash
mkdir -p agents/lesson06_kyc_onboarding
```

Create `agents/lesson06_kyc_onboarding/tools.py`: 

```python
"""KYC field tracking for the account onboarding agent."""

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
        field_name: Which KYC field this is. Must be one of:
            full_name, date_of_birth, residential_address, id_type,
            id_number, employment_status, source_of_funds.
        field_value: The value the customer provided for this field.

    Returns:
        A dict confirming what was recorded, everything collected so
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

A few things here are new compared to Lesson 3's tools. The `tool_context: ToolContext` parameter isn't something the model provides, ADK recognizes this parameter by its type and injects the real context object automatically at call time; the model only ever sees and fills in `field_name` and `field_value` in its function call. This is how a tool gets access to session state at all: without `ToolContext`, a tool function has no way to read or write anything beyond its own arguments and return value.

Inside the function, `tool_context.state.get("kyc_data", {})` reads whatever's already been collected (an empty dict on the very first call), adds the new field, and writes the whole dict straight back with `tool_context.state["kyc_data"] = kyc_data`. **That reassignment matters:** _always write the full value back to its key after modifying it, rather than assuming an in-place mutation on a nested object is enough_, since state changes are tracked as explicit key assignments. The function also writes a second key, `kyc_status`, a short human-readable summary of what's still missing. That second key is what we're about to wire directly into the agent's own instructions.

## Step 2: Build the agent, with state-aware instructions

Create `agents/lesson06_kyc_onboarding/agent.py`:

```python
"""
Lesson 6: Sessions & State.

A KYC onboarding agent for a retail bank's digital account-opening
flow. It collects required customer details one or two at a time
across a multi-turn conversation, tracking progress in session state
so it never re-asks for something it already has.
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
    "progress already shows as collected. Once everything is "
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

Create `agents/lesson06_kyc_onboarding/__init__.py`:

```python
from . import agent
```

The line doing the real work here is `Current progress: {kyc_status?}.` inside the instruction string. Before every single turn, ADK looks for `{...}` patterns in the instruction, and any it finds get replaced with the current value of that key in session state. So on turn one, `{kyc_status?}` resolves to whatever the DTI-style default is (nothing yet, since no field has been recorded), and by turn four, after a couple of tool calls, that same placeholder resolves to a live string like "Still missing: id_type, id_number, employment_status, source_of_funds." The agent is, in effect, being reminded of its own progress on every turn, without you writing a single line of code to manage that reminder yourself.

**The trailing `?` on `{kyc_status?}` is not optional stylistically**, it's functionally required here, and it's worth understanding why. If a state key referenced in an instruction hasn't been set yet and you leave off the `?`, ADK raises an error rather than silently substituting an empty string, since an unmarked placeholder is treated as a required value. Our `kyc_status` key doesn't exist in state until `record_kyc_detail` runs for the first time, which means the very first message of every conversation, before any field has been collected, would crash without the `?`. Marking it optional tells ADK to substitute an empty string instead when the key isn't there yet, which is exactly the behavior we want for a field that only gets populated partway through the conversation.

One more thing worth knowing, since it affects how you test this: the session state you're building up only lives as long as the current `adk run` or `adk web` process keeps running, in this default local setup. Close the CLI or restart the web server, and you're starting from a fresh, empty session next time. That's fine for this lesson, and fine for local development generally, but it's also exactly the gap Lesson 7 picks up: state here is scoped to a single ongoing conversation, not to the customer across separate visits days apart, which is a different concept ADK calls memory.

## Step 3: Run it and watch state build up across turns

```bash
uv run adk run agents/lesson06_kyc_onboarding
```

Have a multi-turn conversation rather than asking everything at once, which is the whole point of this lesson:

```
My name is Priya Sharma
```

The agent should call `record_kyc_detail` for `full_name`, then ask for the next missing item, likely date of birth. Continue:

```
I was born on 14 March 1990
```

You should see it record `date_of_birth` and move on to the next missing field, without repeating anything it already has. Keep going, giving one or two details per message, until you've supplied all seven fields. On the final message, instead of asking for another field, the agent should recognize everything is collected and confirm the application is ready for review.

If you want to see the state itself rather than inferring it from the conversation, `adk web` is more useful here:

```bash
uv run adk web agents
```

Select `lesson06_kyc_onboarding`, have the same step-by-step conversation, and look for the session/state inspector panel in the web UI, it will show you the raw `kyc_data` dictionary and `kyc_status` string growing turn by turn, which is a good way to build real intuition for what's actually being persisted versus what's just being said in the chat.

## If you're coming from LangChain or LangGraph

This maps closely to a LangGraph state graph, where a shared state object flows through every node and any node can read or update it. ADK's session state plays the same role, one shared, mutable store that persists across a conversation's turns. The instruction-templating piece, `{key_name}` inside a plain instruction string, doesn't have a direct one-to-one equivalent in LangGraph, where you'd more typically construct the prompt yourself in code, pulling whatever state values you need into it explicitly. ADK's version trades a bit of that explicitness for convenience: less code to write, at the cost of the templating behavior (like the `?` optional-key requirement) being something you have to know about rather than something visible in your own prompt-building code.

## In this lesson

We gave an agent memory within a single conversation. The KYC onboarding agent now tracks exactly which required fields it's collected and which are still missing, using a tool that reads and writes session state directly, and an instruction that stays aware of that progress automatically through state-aware templating. The agent no longer treats every message as if it were the first one in the conversation.

## In the next lesson

Lesson 7 extends this idea past a single conversation. Session state disappears the moment a session ends, which is fine for a single onboarding flow but not for a relationship manager assistant that needs to remember a client's preferences the next time they reach out, potentially days or weeks later, in an entirely new session. We'll bring in ADK's memory service to carry information across that gap.
