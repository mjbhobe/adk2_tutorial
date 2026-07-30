# Lesson 7b: Long-Running Tools

Lesson 3 gave an agent function tools that return results immediately: EMI calculations, affordability checks, all completing in milliseconds. But real BFSI workflows aren't always that fast. A credit bureau check might take 30 to 60 seconds. An AML (Anti-Money Laundering) screening might take longer still. A document verification pipeline might run for minutes. Asking a customer to simply wait while the conversation hangs isn't a viable user experience, and a tool that blocks for 60 seconds can cause timeouts and resource exhaustion at scale.

That's exactly what `LongRunningFunctionTool` exists to address.

## The problem we're solving

A loan processing desk receives an application and needs to run a credit bureau check before making any lending decision. The bureau's API is not instant: it accepts the request, queues it internally, and responds asynchronously. In a manual process, the officer submits the request and monitors for a response while handling other work. An agent-driven system needs the same ability: signal that a slow operation has been initiated, remain responsive, and surface the result when it arrives, without freezing the entire conversation.

## How LongRunningFunctionTool differs from FunctionTool

A regular `FunctionTool` follows the straightforward pattern from Lesson 3: the model calls it, it runs, it returns a result, the model reads that result and continues. The whole thing happens synchronously within one turn, and the conversation is effectively paused while the tool runs.

`LongRunningFunctionTool` changes the contract at the ADK framework level. When the model requests a long-running tool call, ADK marks that function call event with a `long_running_tool_ids` field. This single flag changes the behaviour of `event.is_final_response()` in a way that matters enormously: an event carrying `long_running_tool_ids` returns `True` from `is_final_response()` immediately, even though the tool hasn't finished yet. The framework surfaces the in-progress state to your application right away rather than waiting.

What this means practically: your `main.py` event loop sees an "intermediate" response it can show to the user immediately ("Your credit check has been submitted and is running..."), while the tool continues executing in the background. Once the tool function actually returns its result, ADK delivers that through the same event stream as a subsequent event. The key thing to understand is that the underlying Python function in your `LongRunningFunctionTool` still runs to completion, it isn't truly asynchronous in the sense of a separate service or webhook. What changes is how ADK presents its progress to the application layer, and the signal it adds to the tool's declaration telling the model not to call it again while it's in progress.

Speaking of that signal: ADK automatically appends the following to every `LongRunningFunctionTool`'s description when it's sent to the model:

```
NOTE: This is a long-running operation. Do not call this tool again
if it has already returned some intermediate or pending status.
```

You don't write this yourself. It's injected by the framework to prevent the model from impatiently re-calling a tool that is already running.

## Step 1: Create the folder structure

From the root folder, run the following commands:

```bash
mkdir -p agents/lesson07b_long_running_tools/credit_check
```

## Step 2: Write the tool

Create `agents/lesson07b_long_running_tools/credit_check/tools.py`:

```python
"""Lesson 7b: Long-Running Tools — credit bureau check tool."""

import time

from google.adk.tools import LongRunningFunctionTool


def run_credit_bureau_check(
    applicant_id: str,
    requested_loan_amount: float,
) -> dict:
    """Initiates a credit bureau check for a loan applicant.

    This is a long-running operation: in a real system, the credit
    bureau API accepts the request and responds asynchronously,
    typically 15 to 60 seconds. The sleep here simulates that latency
    so the lesson runs without real external calls.

    The framework automatically appends a note to this tool's
    description telling the model not to call it again while it is
    already in progress. You do not need to write that note yourself.

    Args:
        applicant_id: The bank's unique identifier for this applicant.
        requested_loan_amount: The loan amount being applied for.

    Returns:
        A dict with the credit score, band, existing obligations, and
        the maximum recommended new loan amount.
    """
    # Simulate the bureau taking a few seconds to respond.
    # In production this would be a real API call with async polling.
    time.sleep(3)

    return {
        "applicant_id": applicant_id,
        "status": "complete",
        "credit_score": 742,
        "credit_band": "Good",
        "total_existing_obligations": 45000.0,
        "recommended_max_new_loan": min(requested_loan_amount, 2500000.0),
        "bureau": "CIBIL",
    }


# Wrap the plain function in LongRunningFunctionTool instead of
# leaving it as a bare function. This is the only change from how
# you'd define a regular function tool in Lesson 3. The function
# itself is identical — no special return type, no generator protocol.
credit_bureau_check = LongRunningFunctionTool(run_credit_bureau_check)
```

The function itself is plain Python, exactly like Lesson 3's tools. The only difference is the last line: wrapping it in `LongRunningFunctionTool` instead of leaving it as a bare callable. ADK inspects the function's signature and docstring the same way it does for a regular `FunctionTool`, so the same docstring-quality rules apply: the model uses the description to decide when and how to call it.

One thing worth being explicit about: the mock `time.sleep(3)` here represents the bureau's real latency. In a production implementation you'd replace this with an actual HTTP call to a bureau API. That API might be synchronous-but-slow (blocking for 30 seconds then returning), or truly asynchronous (accepting your request and giving back a job ID you poll). Either way, the pattern at the ADK level is identical: wrap the function in `LongRunningFunctionTool`, and ADK handles signalling the in-progress state to your application while it waits.

## Step 3: Build the agent

Create `agents/lesson07b_long_running_tools/credit_check/agent.py`:

```python
"""Lesson 7b: Long-Running Tools — loan processing agent."""

from google.adk.agents import Agent

from common.model_config import get_model
from .tools import credit_bureau_check

AGENT_INSTRUCTION = (
    "You are a loan processing assistant for a retail bank. When asked "
    "to run a credit check on an applicant, use the credit bureau check "
    "tool and inform the customer that this will take a moment. Once "
    "the result is back, summarise the credit score, credit band, and "
    "whether the requested loan amount is within the recommended limit. "
    "Never guess or estimate credit scores; only report what the tool "
    "returns."
)

root_agent = Agent(
    name="credit_check_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description="Runs credit bureau checks for loan applicants.",
    tools=[credit_bureau_check],
)
```

Create `agents/lesson07b_long_running_tools/credit_check/__init__.py`:

```python
from . import agent
```

Notice that `credit_bureau_check` (the wrapped `LongRunningFunctionTool` instance) goes directly into the `tools` list, not the underlying `run_credit_bureau_check` function. This matters: if you accidentally pass the bare function, ADK creates a regular `FunctionTool` with `is_long_running=False`, and the framework won't signal the in-progress state to your application.

## Step 4: Write main.py

You're already familiar with `main.py` from Lesson 6a — the `Runner`, `SessionService`, and async event loop are all the same. The only meaningful difference in this lesson is in how you consume the event stream, and it matters.

The event-loop handling needs a small but important addition compared to earlier lessons. Because `event.is_final_response()` returns `True` on the long-running tool call event itself (before the tool finishes), you'll see two "final response" events in a single turn: one carrying the model's "I'm running the check now" message, and one carrying its summary of the result once the tool completes. A naive loop that breaks on the first `is_final_response()` would miss the actual result.

Create `agents/lesson07b_long_running_tools/main.py`:

```python
"""Lesson 7b: Long-Running Tools — credit bureau check.

Demonstrates how LongRunningFunctionTool surfaces an in-progress
state to the application while the slow operation runs, rather than
freezing the conversation until it completes.

Run with:
    uv run agents/lesson07b_long_running_tools/main.py
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

from credit_check.agent import root_agent

APP_NAME = "credit_check_app"
USER_ID = "demo_user"


async def main() -> None:
    """Runs a console loan processing conversation with a long-running tool."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
    )

    print("Loan Processing Assistant (type 'exit' to quit)\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        user_message = types.Content(
            role="user", parts=[types.Part(text=user_input)]
        )

        # Unlike earlier lessons, we do NOT break on the first
        # is_final_response() event. With a long-running tool, two
        # events carry is_final_response()=True in one turn:
        #   1. The model's "check is running" message (before tool completes)
        #   2. The model's result summary (after tool completes)
        # Collecting all final-response text and printing it at the end
        # gives the user a coherent, complete answer.
        response_parts = []
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session.id,
            new_message=user_message,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                text = "".join(
                    part.text for part in event.content.parts if part.text
                )
                if text:
                    response_parts.append(text)

        if response_parts:
            print(f"Agent: {' '.join(response_parts)}\n")


if __name__ == "__main__":
    asyncio.run(main())
```

The key difference from every previous `main.py` is visible in the event loop: instead of printing immediately on the first `is_final_response()` event and moving on, we collect all final-response text across the whole turn before printing. This is what ensures the customer sees a single, coherent response that includes both the "I'm running the check" acknowledgement and the actual result, rather than the application printing halfway through and leaving the result stranded.

## Step 5: Run it

From the root folder, run the following command:

```bash
uv run agents/lesson07b_long_running_tools/main.py
```

Try a credit check request:

```
Please run a credit bureau check for applicant ID LOAN2024-001,
who is applying for a loan of 1,500,000 rupees.
```

You'll notice a pause of about three seconds (the simulated bureau latency), then a response summarising the credit score (742, Good band) and confirming the requested amount is within the recommended limit. The pause is the tool running. In `adk web`, which you can also use here (`adk web agents/lesson07b_long_running_tools`), the in-progress state is slightly more visible: you'll see the model's initial acknowledgement appear, then the result follow after the tool completes.

## A note on truly asynchronous patterns

What we built here is a long-running-but-synchronous tool: it blocks for the duration of the operation and returns a final result in one go. This covers the majority of real BFSI cases (slow API calls, database queries, document processing pipelines).

ADK also supports a genuinely asynchronous pattern where a tool returns `None` immediately (signalling "I've submitted the request, result will come later"), and your application submits the tool's result back to the runner in a subsequent `run_async` call by passing a `types.Content` with a `function_response` part carrying the original `function_call_id`. This is the webhook/polling model: your application fires off the tool, does other things, receives the result via a callback, and injects it back. That pattern is more complex to implement and requires your application to persist the `function_call_id` between calls, which moves it well beyond a single-lesson example. The ADK documentation covers it if you need it, but for the vast majority of BFSI use cases, the synchronous-but-slow pattern above is the right fit.

## If you're coming from LangChain or LangGraph

LangChain doesn't have a direct equivalent to `LongRunningFunctionTool` as a first-class primitive. The closest analogue is wrapping a long-running operation in a `RunnableConfig` with a timeout and streaming the intermediate state through a custom callback handler. LangGraph's async node execution is more naturally suited to this kind of operation, since you can define a node that yields intermediate state while waiting. ADK's `LongRunningFunctionTool` sits somewhere between the two: it's a first-class framework primitive rather than something you assemble from lower-level pieces, but it's also more constrained than LangGraph's full async node model.

## In this lesson

We extended the tool model from Lesson 3 with `LongRunningFunctionTool`, a wrapper that signals to ADK and to the model that a tool call may take significant time. The underlying function is unchanged, plain Python returning a dict, and the registration change is a single line: wrapping it in `LongRunningFunctionTool` instead of passing it bare. The main application change is collecting all final-response events across a turn rather than stopping at the first one, since a long-running tool turn produces two.

## In the next lesson

Lesson 8 introduces ADK's long-term memory service, letting an agent recall information from entirely separate sessions rather than just the current conversation. We'll use the `add_session_to_memory` pattern you've already seen in Lesson 7a's callback, and build a relationship manager assistant that remembers client preferences across separate conversations.
