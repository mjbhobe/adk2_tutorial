# Lesson 6c: Artifacts

Lessons 6a and 6b gave an agent two ways to remember things within and across a session: pre-seeded state from the application, and tool-driven state from inside a function. Both of those mechanisms share a common constraint: they store small, structured data. A string, a number, a dictionary — things you'd be comfortable putting in a JSON field.

But what do you do when a tool generates something large and binary, like a PDF report, a CSV export, a generated image, or a downloaded document? You wouldn't stuff a 500KB PDF into a state dictionary. Artifacts give you a separate, named storage layer specifically for file-like objects, backed by an `ArtifactService` wired into the `Runner`.

## The problem we're solving

A retail bank's loan processing desk generates a summary document for every loan application: applicant name, loan amount, EMI, total interest, total repayment. Customers want this as a PDF they can save. Today a loan officer calculates the figures manually and produces a Word document. We're going to build an agent that does both steps — calculates the figures and generates the PDF — and saves the result as a retrievable artifact that `main.py` can write to disk.

## State versus artifacts — the distinction that matters

Session state is a key-value dictionary. It's designed for small, structured values: `{"kyc_status": "Still missing: id_number"}`, `{"turn_count": 4}`. You read individual keys, write individual keys, and the whole thing is meant to be inspectable and comparable at a glance.

Artifacts are for file-like objects: PDFs, CSVs, images, Word documents, anything binary or large. They're stored separately from state, backed by an `ArtifactService` (distinct from `SessionService`), and retrieved by filename and version rather than by key. Each time you save an artifact with the same filename, ADK creates a new version rather than overwriting — so you always have access to the history.

The scoping rules also differ subtly. A plain artifact filename like `"loan_summary.pdf"` is scoped to the current session. A filename prefixed with `user:`, like `"user:loan_summary.pdf"`, is scoped to the user across all their sessions — useful for documents that should persist beyond one conversation.

## Step 1: Install the required package

We'll use `reportlab` to generate PDFs in Python. It's free, pure-Python, and straightforward:

```bash
uv add reportlab
```

## Step 2: Create the folder structure

```bash
mkdir -p agents/lesson06c_artifacts/loan_report
```

## Step 3: Write the tool

This is the first tool in the series that is `async def` rather than a plain `def`. That's not optional: `tool_context.save_artifact()` is an async method, and calling an async method from inside a synchronous function requires awkward workarounds. ADK supports async tool functions natively, so the right approach is simply to make the tool itself async.

Create `agents/lesson06c_artifacts/loan_report/tools.py`:

```python
"""Lesson 6c: Artifacts — loan summary PDF tool.

This tool is async because tool_context.save_artifact() is an async
method. ADK supports async tool functions natively — the only change
from a regular tool is the `async def` and `await` keyword.
"""

import io

from google.adk.tools import ToolContext
from google.genai import types
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


async def calculate_loan_summary(
    tool_context: ToolContext,
    applicant_name: str,
    principal: float,
    annual_interest_rate_percent: float,
    tenure_months: int,
) -> dict:
    """Calculates loan figures and saves a PDF summary report as an artifact.

    Args:
        tool_context: Injected by ADK; required to save the PDF artifact.
        applicant_name: Full name of the loan applicant.
        principal: Loan amount in INR.
        annual_interest_rate_percent: Annual interest rate as a percentage.
        tenure_months: Loan tenure in months.

    Returns:
        A dict with the calculated figures and the artifact filename and
        version number assigned by the artifact service.
    """
    monthly_rate = (annual_interest_rate_percent / 100) / 12
    growth_factor = (1 + monthly_rate) ** tenure_months
    emi = principal * monthly_rate * growth_factor / (growth_factor - 1)
    total_payment = emi * tenure_months
    total_interest = total_payment - principal

    # Build the PDF in memory using reportlab.
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    _, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, height - 72, "Loan Summary Report")

    y = height - 120
    rows = [
        ("Applicant", applicant_name),
        ("Loan Amount", f"INR {principal:,.2f}"),
        ("Annual Interest Rate", f"{annual_interest_rate_percent}%"),
        ("Tenure", f"{tenure_months} months ({tenure_months // 12} years)"),
        ("Monthly EMI", f"INR {emi:,.2f}"),
        ("Total Interest Payable", f"INR {total_interest:,.2f}"),
        ("Total Amount Payable", f"INR {total_payment:,.2f}"),
    ]
    for label, value in rows:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, y, f"{label}:")
        c.setFont("Helvetica", 11)
        c.drawString(240, y, value)
        y -= 26

    c.save()
    pdf_bytes = buffer.getvalue()

    # Wrap the raw bytes in a types.Part — ADK's standard container for
    # binary data, carrying both the bytes and the MIME type together.
    filename = f"loan_summary_{applicant_name.replace(' ', '_')}.pdf"
    artifact = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")

    # save_artifact is async — hence `await` and `async def` on this function.
    # It returns a version number; version 0 is the first save, 1 the second, etc.
    version = await tool_context.save_artifact(filename=filename, artifact=artifact)

    return {
        "applicant_name": applicant_name,
        "monthly_emi": round(emi, 2),
        "total_interest": round(total_interest, 2),
        "total_payment": round(total_payment, 2),
        "artifact_filename": filename,
        "artifact_version": version,
    }
```

Two new ADK pieces appear here that haven't come up before.

`types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")` wraps raw binary data into a `Part` — ADK's standard container for content, whether that content is text, image, audio, or a file. The `mime_type` tells any downstream consumer what kind of data it's holding.

`await tool_context.save_artifact(filename=filename, artifact=artifact)` saves the `Part` to the `ArtifactService` configured on the `Runner`. It returns an integer version number, starting at 0 for the first save of a given filename. If you save the same filename again in a later turn, version 1 is created alongside version 0 — nothing is overwritten.

## Step 4: Build the agent

Create `agents/lesson06c_artifacts/loan_report/agent.py`:

```python
"""Lesson 6c: Artifacts — loan documentation agent."""

from google.adk.agents import Agent

from common.model_config import get_model
from .tools import calculate_loan_summary

AGENT_INSTRUCTION = (
    "You are a loan documentation assistant for a retail bank. "
    "When a customer provides their loan details, use the "
    "calculate_loan_summary tool to compute the figures and generate "
    "a PDF summary report. After the tool runs, confirm the monthly EMI "
    "and total repayment to the customer, and let them know their "
    "summary report has been saved as a PDF document they can download."
)

root_agent = Agent(
    name="loan_report_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description="Calculates loan figures and generates a PDF summary as an artifact.",
    tools=[calculate_loan_summary],
)
```

Create `agents/lesson06c_artifacts/loan_report/__init__.py`:

```python
from . import agent
```

## Step 5: Write main.py

`main.py` introduces one new object — `InMemoryArtifactService` — and wires it into the `Runner` alongside the session service. It also shows how to retrieve a saved artifact and write it to disk after the agent's turn completes.

Create `agents/lesson06c_artifacts/main.py`:

```python
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
```

The artifact retrieval pattern after the event loop is worth reading carefully. `event.actions.artifact_delta` is a dictionary of `{filename: version}` entries, one for each artifact saved during the current turn. We capture the filename while streaming events, then retrieve the full artifact after the loop completes rather than inside it — this keeps the event loop tight and avoids making additional async calls mid-stream.

`artifact_service.load_artifact(...)` returns a `types.Part` whose `inline_data.data` is the raw bytes. `out_path.write_bytes(...)` writes those bytes straight to disk. The file that appears on disk is a real, openable PDF.

## Step 6: Run it

Run the following commands from the root (`adk2_tutorial`) folder

```bash
source .venv/bin/activate
uv run agents/lesson06c_artifacts/main.py
```

Ask the agent to generate a loan summary:

```
Please generate a loan summary for Priya Sharma, 
loan amount 2,500,000 rupees, 
interest rate 8.5%, tenure 20 years.
```

You should see the agent respond with the key figures — monthly EMI, total interest, total repayment — and confirm the report has been saved. Below the agent's response, `main.py` will print a line like:

```
[PDF saved to: /path/to/your/project/loan_summary_Priya_Sharma.pdf]
```

Open that file in any PDF viewer and you'll find a formatted one-page loan summary document.

## Artifacts versus state: the practical rule

| | Session State | Artifacts |
|---|---|---|
| **What it stores** | Small key-value data | Binary/file-like objects |
| **API** | `tool_context.state["key"] = value` | `await tool_context.save_artifact(filename, part)` |
| **Retrieval** | `tool_context.state.get("key")` | `await artifact_service.load_artifact(filename)` |
| **Versioning** | Overwrites in place | New version per save |
| **Scoping** | Session or user (via prefix) | Session or user (via `user:` prefix on filename) |
| **Good for** | Progress flags, collected fields, scores | PDFs, CSVs, images, documents |

## If you're coming from LangChain or LangGraph

LangChain doesn't have a first-class artifact concept. The closest pattern is writing to a file or a blob store inside a tool yourself, then passing a URL or file path back through the conversation. ADK's artifact system standardises that pattern: the service, the versioning, and the retrieval are all handled by the framework rather than something you wire up per-tool. The `tool_context.save_artifact` / `artifact_service.load_artifact` pair is the ADK equivalent of your own file-storage logic, but with versioning and scoping built in.

## In this lesson

We gave an agent the ability to produce and store file-like output. The loan documentation agent now generates a real PDF and saves it as a versioned artifact via `tool_context.save_artifact()`, with `main.py` retrieving and writing it to disk after the turn completes. The key new pattern is the `async def` tool — required whenever a tool calls an async ADK method — and the `artifact_delta` on the event's actions, which signals that an artifact was saved during the turn.

## In the next lesson

Lesson 7 introduces Callbacks — six hook points that fire automatically at different moments in every turn, letting you add cross-cutting behaviour like guardrails, logging, and compliance scanning without touching the agent's core logic.
