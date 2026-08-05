# Lesson 11c: LoopAgent in Practice

Quick recap: `LoopAgent` runs a sub-agent, or a small sequence of sub-agents, repeatedly, until either a sub-agent signals an exit (by escalating) or a `max_iterations` cap is hit. Unlike `SequentialAgent`, there's no fixed number of steps ahead of time, and unlike `ParallelAgent`, nothing runs concurrently, one turn finishes completely before the next one starts. Always set `max_iterations`, even when you're confident the exit logic is correct, it's the safety net for the case where it isn't. Let's get onto building it.

## The problem we're solving

You're building the document verification step of the same NBFC's KYC onboarding flow: an applicant submits their Aadhaar document (India's 12-digit biometric ID), and the system checks it. Real-world document uploads fail more often than you'd like, a blurry photo, an expired document, a name that doesn't quite match the application. When that happens, you don't want to reject the applicant outright, you want to ask them to try again, automatically, up to a reasonable number of attempts, before involving a human.

That's a loop with two exit conditions: success (the document passes) or exhaustion (too many failed attempts). `SequentialAgent` can't express this, it has no concept of "repeat this step." `LoopAgent` is built for exactly this shape.

> 📌 **NOTE:** A real production version of this loop would pause after a failed attempt and wait for the applicant to actually upload a new photo, a human-in-the-loop pattern this series hasn't covered yet. This lesson's `LoopAgent` runs entirely within one request, so each "retry" is simulated by a tool call standing in for that upload, rather than a live wait. The loop mechanics you're about to build, retry, exit condition, safety cap, are the same either way, what differs in a real system is what happens between attempts, not how the loop itself decides when to stop.

## How the exit condition actually works

This is the one piece of machinery in this lesson that's genuinely new, and it's worth being precise about, since it's easy to wave your hands at "the agent escalates" without knowing what that means in code.

**`LoopAgent` doesn't decide when to stop by inspecting your data. It stops when it sees an event with `escalate` set to `True`, checked after every single event any sub-agent produces. That flag doesn't come from the LLM's text response, it comes from a tool**. A tool function can declare a parameter typed `ToolContext`, and ADK automatically supplies it, the model never has to know it exists or provide it as an argument. Inside that tool, setting `tool_context.actions.escalate = True` is what actually reaches `LoopAgent`, because ADK attaches the tool's `actions` directly to the event it creates for that tool call.

Practically, this means the exit condition lives in a small, dedicated tool, not scattered through the main verification logic:

```python
def exit_document_loop(tool_context: ToolContext) -> dict:
    tool_context.actions.escalate = True
    return {"status": "loop_exit_requested"}
```

The agent's instruction tells the model to call this tool only when verification actually passed. If it never passes, the model never calls it, and `max_iterations` is what eventually stops the loop instead.

## Step 1: Set up the folder structure

```
agents/lesson11c_loop_agent/
├── main.py
├── api.py
├── streamlit_app.py
└── document_pipeline/
    ├── __init__.py
    ├── agent.py
    └── sub_agents/
        ├── __init__.py
        └── document_review_agent/
            ├── __init__.py
            ├── agent.py
            └── tools.py
```

Only one sub-agent this time, `document_review_agent`, the thing `LoopAgent` repeats. `LoopAgent` can run a short sequence of sub-agents per iteration if a scenario calls for it, but this one doesn't need more than one.

## Step 2: Build the document review agent's tools

Two tools: one that simulates an attempt (resubmission plus verification, combined for this lesson), and the small exit-signaling tool from above.

Create `agents/lesson11c_loop_agent/document_pipeline/sub_agents/document_review_agent/tools.py`

```python
"""Lesson 11c: Tools for the document review agent.
"""

import hashlib

from google.adk.tools import ToolContext


def submit_and_check_document(
    applicant_name: str, 
    aadhaar_number: str, 
    attempt_number: int,
) -> dict:
    """Simulates a customer resubmitting their Aadhaar document and the system verifying it.

    In a real onboarding flow, the customer uploads a fresh photo of their
    document at this point, and the system runs OCR (Optical Character
    Recognition) plus a records match against it. Both steps are combined
    and mocked here as one deterministic call, standing in for a live
    photo upload that this lesson's single, non-interactive run can't
    wait for. A production version of this loop would pause after a
    failed attempt and resume once the next upload actually arrives,
    a human-in-the-loop pattern this series hasn't covered yet.

    Args:
        applicant_name: The applicant's full name.
        aadhaar_number: The applicant's 12-digit Aadhaar number.
        attempt_number: Which attempt this is, 1 for the first submission.

    Returns:
        A dict with:
            attempt_number (int): Echoes the attempt number passed in.
            passed (bool): True if this submission cleared verification.
            issue (str, optional): Present only when passed is False, a
                short description of what went wrong.
    """
    digest = hashlib.sha256(f"{applicant_name}|{aadhaar_number}|{attempt_number}".encode()).hexdigest()
    seed = int(digest[:8], 16)

    passed = (seed % 3) != 0  # roughly 2 in 3 attempts pass, independently each time

    if passed:
        return {"attempt_number": attempt_number, "passed": True}

    issues = [
        "Image too blurry to read",
        "Document appears expired",
        "Name does not match application",
    ]
    return {
        "attempt_number": attempt_number,
        "passed": False,
        "issue": issues[seed % len(issues)],
    }


def exit_document_loop(tool_context: ToolContext) -> dict:
    """Signals that the document retry loop should stop, verification passed.

    Sets escalate on the tool context's actions. LoopAgent checks this
    flag after every event its sub-agents produce, and stops repeating as
    soon as it sees escalate set to True, rather than waiting for
    max_iterations.

    Args:
        tool_context: Supplied automatically by ADK because this
            function declares a ToolContext-typed parameter. The model
            never provides this argument itself.

    Returns:
        A short acknowledgement dict.
    """
    tool_context.actions.escalate = True
    return {"status": "loop_exit_requested"}
```

Notice `submit_and_check_document` doesn't know anything about looping, exit conditions, or attempt limits, it just answers "did this specific attempt pass." All of the loop-control logic lives in the second, much smaller tool. That separation keeps the verification logic testable on its own, exactly the same reasoning that put deterministic formulas in their own tools throughout Lesson 11a and 11b.

## Step 3: Build the document review agent

Create `agents/lesson11c_loop_agent/document_pipeline/sub_agents/document_review_agent/agent.py`

```python

"""Lesson 11c: Document review agent, the sub-agent LoopAgent repeats.

Each time LoopAgent runs this agent, it's one attempt at verifying the
applicant's Aadhaar document. It tracks the attempt number through its
own previous result in session state, and calls exit_document_loop only
once verification actually passes, letting LoopAgent's max_iterations
act as the safety net for the case where it never does.
"""

from typing import Optional

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import exit_document_loop, submit_and_check_document


class DocumentCheckResult(BaseModel):
    """Structured output of the document review agent, written every attempt."""

    attempt_number: int = Field(description="Which attempt this was, 1 for the first submission")
    passed: bool = Field(description="True if this submission cleared verification")
    issue: Optional[str] = Field(default=None, description="Present only when passed is False")


instruction = """You are the document review agent for a KYC (Know Your
Customer) onboarding check at an NBFC. Your job is to verify an
applicant's Aadhaar document, one attempt per turn, retrying automatically
until it passes or the retry limit is reached.

The applicant's name and Aadhaar number are in the original request.
Session state may already hold a result from an earlier attempt:
{document_check_result?}

If document_check_result is present, this is a retry, use its
attempt_number plus 1 as this attempt's number. If it's not present,
this is the first attempt, attempt_number is 1.

1. Call `submit_and_check_document` with applicant_name, aadhaar_number,
   and this attempt's attempt_number.
2. If the tool reports passed as True, call `exit_document_loop` to stop
   the retry loop. If passed is False, do not call it, just let this
   turn end normally.
3. Either way, respond with the structured fields, echoing exactly what
   `submit_and_check_document` returned.

Always call submit_and_check_document first. Only call exit_document_loop
when verification actually passed.

Respond with the structured fields only. No markdown, no headers, no
commentary, just the fields the schema requires.
"""

document_review_agent = Agent(
    name="document_review_agent",
    model=get_model("primary"),
    description="Verifies an applicant's Aadhaar document, one attempt per turn, signaling exit once it passes.",
    instruction=instruction,
    tools=[submit_and_check_document, exit_document_loop],
    output_schema=DocumentCheckResult,
    output_key="document_check_result",
)
```

`{document_check_result?}` is the same optional-templating syntax you've seen implicitly all along, the trailing `?` means "substitute an empty string if this key doesn't exist yet, don't error." That's exactly the situation on the very first attempt, before this agent has ever written to state. Every attempt after that, the same key holds the previous attempt's result, which is how this single agent knows which attempt number it's on without any external counter.

## Step 4: Assemble the LoopAgent

Create `agents/lesson11c_loop_agent/document_pipeline/agent.py`

```python
"""Lesson 11c: LoopAgent that retries Aadhaar document verification.

Repeats document_review_agent until it either signals escalate (the
document passed) or max_iterations is reached (three attempts, then
the case goes to a human regardless of what the last attempt found).
"""

from google.adk.agents import LoopAgent

from .sub_agents.document_review_agent.agent import document_review_agent

root_agent = LoopAgent(
    name="document_retry_loop",
    description="Retries Aadhaar document verification up to three times, or until it passes.",
    sub_agents=[document_review_agent],
    max_iterations=3,
)
```

Three fields, `name`, `sub_agents`, and this time `max_iterations`, which neither `SequentialAgent` nor `ParallelAgent` needed, because both of those always know exactly how many steps they're running. `LoopAgent` doesn't, by design, so it needs an explicit cap.

## Step 5: Wire up main.py

One thing worth knowing before you write this: unlike Lesson 11b's `ParallelAgent`, there's no race condition to work around here. `LoopAgent` runs one turn at a time, so whichever attempt ran last really is the last thing that happened, no interleaving. `main.py` still reads the result from session state rather than the raw returned text, but for a more ordinary reason, structured fields are easier to work with than a block of text.

Create `agents/lesson11c_loop_agent/main.py`

```python
"""Lesson 11c: Run the document verification LoopAgent pipeline.
"""

import asyncio
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # adds agents/ for common.*

from google.adk.sessions import InMemorySessionService

from common.runner_utils import run_agent_query
from document_pipeline.agent import root_agent

APP_NAME = "lesson11c_loop_agent"


async def main() -> None:
    """Runs the document retry loop against console input."""
    session_service = InMemorySessionService()
    user_id = "console_user"

    print("Document verification (LoopAgent, up to 3 attempts).")
    print("Paste an applicant's name and Aadhaar number, or type 'quit' to exit.\n")

    loop = asyncio.get_event_loop()
    while True:
        try:
            user_input = await loop.run_in_executor(None, lambda: input("Application: "))
        except EOFError:
            break

        if user_input.strip().lower() in ("quit", "exit"):
            break

        # A fresh session per application: each document check is a
        # one-shot run, not an ongoing conversation.
        session_id = str(uuid.uuid4())

        await run_agent_query(
            agent=root_agent,
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            query=user_input,
            session_service=session_service,
        )

        # Unlike Lesson 11b's ParallelAgent, there's no race here,
        # LoopAgent runs one turn at a time, so run_agent_query's final
        # response text really is whichever attempt ran last. State is
        # still the better place to read the result from, though: it's
        # already a parsed dict with attempt_number, passed, and issue
        # as separate fields, rather than a block of text to parse by hand.
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

        # show intermediate "retry" attempts, if any
        for event in session.events:
        attempt = event.actions.state_delta.get("document_check_result")
        if attempt:
            print(" attempt:", attempt)

        result = session.state.get("document_check_result")
        print("\nFinal result:", result)
        if result and result.get("passed"):
            print(f"Verified after {result['attempt_number']} attempt(s).")
        else:
            print("Retries exhausted without a pass. Refer to manual review.")
        print()


if __name__ == "__main__":
    asyncio.run(main())
```

## Step 6: Run it

Run the following command in a new terminal from the project root folder (`adk2_tutorial`).

```bash
# activate local environment (Mac/Linux)
source .venv/bin/activate  # (or source .venv/Scripts/activate on Windows)
# run the file
uv run agents/lesson11c_loop_agent/main.py
```

Paste in an applicant whose first attempt fails but second one passes:

```
Application: Verify the Aadhaar document for Sanya Bhatt, Aadhaar number 918273641001.
```

The first attempt should fail with "Image too blurry to read," and the loop should automatically retry, the second attempt should pass, calling `exit_document_loop` and stopping there, two attempts total, one short of the three-attempt cap. `main.py` should report it verified after 2 attempts.

Now try an applicant whose document never clears in three tries:

```
Application: Verify the Aadhaar document for Anil Agarwal, Aadhaar number 987654320023.
```

All three attempts should fail. Nothing ever calls `exit_document_loop`, so `max_iterations` is what actually stops the loop this time, not the exit condition. `main.py` should report retries exhausted, referred to manual review, with the last attempt's issue still visible in the final result.

Running these two side by side is the whole point of this lesson: the same agent, the same tools, the same loop, and two completely different numbers of iterations, because the loop genuinely responds to what happens inside it rather than following a fixed script the way `SequentialAgent` or `ParallelAgent` would.

## Try it in adk web too

Point `adk web` at the whole `agents/` folder, same reason as the last two lessons, `common` only resolves correctly when `agents/` itself is on the Python path:

```bash
adk web agents
```

Look for `lesson11c_loop_agent.document_pipeline` in the dropdown. You'll also see one extra entry for the sub-agent folder itself, ignore it.

Select `lesson11c_loop_agent.document_pipeline`, paste in Anil Agarwal's application, and watch the trace panel. This is the clearest place to actually see a loop happen: the same agent's name appears three separate times in the trace, once per attempt, each with its own tool call and its own structured output, rather than the single turn you'd see from a `SequentialAgent` step.

> **NOTE:** As in the last two lessons, `adk web` is a development and inspection tool, not how this pipeline gets called in production. `main.py`, or the FastAPI server built next, is for that.

## Serving this behind an API and a Streamlit form

### FastAPI, wrapping the pipeline

Same shape as the last two lessons' `api.py`: a shared `session_service`, a thin endpoint, `run_agent_query` to drive the run, the response read back from `session.state`.

```python
# agents/lesson11c_loop_agent/api.py
"""Lesson 11c: FastAPI server for the document verification LoopAgent.

Same shape as Lesson 11a's and 11b's api.py: a shared session_service, a
thin endpoint, run_agent_query to drive the run, and the response read
back from session.state.

Run with:
    uv run agents/lesson11c_loop_agent/api.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # adds agents/ for common.*

from fastapi import FastAPI
from google.adk.sessions import InMemorySessionService
from pydantic import BaseModel

from common.runner_utils import run_agent_query
from document_pipeline.agent import root_agent
from document_pipeline.sub_agents.document_review_agent.agent import DocumentCheckResult

APP_NAME = "lesson11c_loop_agent"

# Created once, shared across every HTTP request, same pattern as Lesson 9, 11a, and 11b.
session_service = InMemorySessionService()
app = FastAPI(title="Document Verification Loop API")


class DocumentCheckRequest(BaseModel):
    """The shape of an incoming request to /verify-document."""

    user_id: str
    session_id: str
    application_text: str


class DocumentCheckResponse(BaseModel):
    """The shape of a response from /verify-document.

    result is whichever attempt the loop ended on, either the one that
    passed, or the final attempt if all three failed.
    """

    result: DocumentCheckResult


@app.get("/health")
async def health() -> dict:
    """Simple liveness check, useful once this is deployed."""
    return {"status": "ok"}


@app.post("/verify-document", response_model=DocumentCheckResponse)
async def verify_document(request: DocumentCheckRequest) -> DocumentCheckResponse:
    """Runs the document retry loop and returns the final attempt's result."""
    await run_agent_query(
        agent=root_agent,
        app_name=APP_NAME,
        user_id=request.user_id,
        session_id=request.session_id,
        query=request.application_text,
        session_service=session_service,
    )

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=request.user_id, session_id=request.session_id
    )

    return DocumentCheckResponse(result=session.state["document_check_result"])


if __name__ == "__main__":
    import uvicorn

    # A different port from Lesson 11a (8080) and 11b (8081).
    uvicorn.run(app, host="127.0.0.1", port=8082)
```

Notice the response only ever contains one result, not a list of every attempt. The API's caller doesn't need to know or care how many retries happened internally, only how it ended, exactly the way a loop's caller should be able to treat it as a single operation regardless of how many times it looped underneath.

Run it:

```bash
uv run agents/lesson11c_loop_agent/api.py
```

Open `http://127.0.0.1:8082/docs` and try `/verify-document` directly before building any client.

### A Streamlit form for document verification

```python
# agents/lesson11c_loop_agent/streamlit_app.py
"""Lesson 11c: Streamlit front-end for document verification.

Collects the applicant's name and Aadhaar number, assembles them into
the sentence-shaped text the agent expects, and sends that to the API's
/verify-document endpoint. The retry loop runs entirely inside that one
request, this form only ever sees the final result.

Run this alongside api.py in a separate terminal, not instead of it.

Run with:
    streamlit run agents/lesson11c_loop_agent/streamlit_app.py
"""

import uuid

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8082/verify-document"

st.set_page_config(page_title="Document Verification", page_icon="📄")
st.title("KYC Document Verification")
st.caption(
    "A dummy front-end standing in for a real onboarding screen. "
    "It knows nothing about ADK; it only talks to our pipeline's API."
)

if "user_id" not in st.session_state:
    st.session_state.user_id = f"streamlit-user-{uuid.uuid4().hex[:8]}"

with st.form("document_check"):
    applicant_name = st.text_input("Full name")
    aadhaar_number = st.text_input("Aadhaar number (12 digits)")
    submitted = st.form_submit_button("Verify document")

if submitted:
    application_text = (
        f"Verify the Aadhaar document for {applicant_name}, "
        f"Aadhaar number {aadhaar_number}."
    )

    with st.spinner("Verifying, retrying automatically if needed..."):
        response = requests.post(
            API_URL,
            json={
                "user_id": st.session_state.user_id,
                "session_id": f"session-{uuid.uuid4().hex[:8]}",
                "application_text": application_text,
            },
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()["result"]

    if result["passed"]:
        st.success(f"Verified after {result['attempt_number']} attempt(s).")
    else:
        st.error(f"Verification failed after {result['attempt_number']} attempt(s). Referred to manual review.")
        if result.get("issue"):
            st.write(f"Last issue: {result['issue']}")

    st.json(result)
```

Notice there's no loading indicator per attempt, no "retrying, attempt 2 of 3" message. From Streamlit's side, one form submission produces exactly one spinner and one result, the retries are entirely an implementation detail of what happens behind that one API call. That's a genuine UX consideration worth sitting with: a real onboarding screen might want to show retry progress live, which would need the human-in-the-loop pattern flagged earlier in this lesson, not the single-request loop built here.

Run it alongside `api.py`, in a separate terminal:

```bash
streamlit run agents/lesson11c_loop_agent/streamlit_app.py
```

## If you're coming from LangChain or LangGraph

In LangGraph, this maps to a cycle: a node with a conditional edge that routes back to itself when the exit condition isn't met, and forward to `END` (or the next node) when it is. `max_iterations` corresponds to a counter you'd typically thread through the graph's state yourself and check in that same conditional edge, LangGraph doesn't enforce an iteration cap for you the way `LoopAgent` does.

The exit mechanism itself is conceptually similar to what you just built: some piece of code decides "stop now," and that decision routes control flow rather than being embedded in the main task logic. LangGraph makes you wire that as an explicit edge condition. ADK's version is a tool setting a flag on its own context, arguably a smaller surface, since the exit condition lives entirely inside the sub-agent that already has the context to decide, rather than in a separate routing function that has to be told what that sub-agent found.

## In this lesson

You built a working `LoopAgent` that retries Aadhaar document verification, up to three attempts, exiting early the moment a submission passes. You saw the actual mechanism behind that exit, verified against ADK's source rather than taken on faith: a tool sets `tool_context.actions.escalate`, that becomes the function-response event's `actions`, and `LoopAgent` checks that flag after every event any sub-agent produces. You saw `{document_check_result?}`'s optional-templating syntax let a single agent track its own attempt count purely through what it previously wrote to state, no external counter needed. And you saw, concretely, that `LoopAgent` has no race condition the way `ParallelAgent` did, one turn finishes before the next starts, so reading results from session state here is about convenience, not correctness.

## In the next lesson

You've now built all three classic workflow agents, fixed order, concurrent, and repeating, each with its own coding lesson and its own FastAPI and Streamlit front end. The next lesson moves away from orchestrating agents you've already built, and toward giving an agent access to tools it doesn't own, MCP (Model Context Protocol) servers, `McpToolset`, and building a small MCP server of your own around mutual fund NAV (Net Asset Value) data.
