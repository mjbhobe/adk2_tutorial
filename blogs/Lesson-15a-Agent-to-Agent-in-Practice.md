# Lesson 15a: Agent-to-Agent Delegation in Practice

Lesson 15 covered A2A, an open protocol for one agent to reach a genuinely separate agent, running in its own process, described through a standard Agent Card. This lesson builds it for real: `risk_specialist_agent`, the same one from 13a, run as its own A2A server, and a loan orchestrator that reaches it two different ways, `AgentTool` for a model's own judgment call, and a plain sub-agent in a fixed `SequentialAgent` pipeline.

## Step 1: Install what this needs

From a new terminal run the following commands from the project root folder (`adk2_tutorial`):

```bash
source .venv/bin/activate
uv add "google-adk[a2a]==2.5.0" sse_starlette
```

`google-adk[a2a]` gives you `to_a2a()` and `RemoteA2aAgent`. `sse_starlette` is a separate dependency the `a2a` SDK's server routing needs, only required for the server side, `risk_service.py` below, not for the consuming side.

## Step 2: Set up the folder structure

```
agents/lesson15a_a2a/
├── main.py
├── risk_service.py
├── peek_raw_task.py
├── risk_specialist/
│   ├── __init__.py
│   ├── agent.py
│   └── tools.py
└── loan_orchestrator/
    ├── __init__.py
    └── agent.py
```

`risk_specialist/agent.py` is a plain agent definition, the same shape every other agent file in this series has. `risk_service.py`, at the top level, is what actually turns it into an A2A server. `loan_orchestrator/` is the consuming side.

## Step 3: The risk-scoring tool, reused from 13a

Create `agents/lesson15a_a2a/risk_specialist/tools.py`

```python 
"""Lesson 15a: The risk-scoring tool, reused unchanged from 13a.
"""

def calculate_risk_score(
    credit_score: int,
    annual_income: float,
    loan_amount: float,
    tenure_months: int,
    has_defaults: bool,
) -> dict:
    """Calculates a deterministic risk score for a loan application.

    Args:
        credit_score: CIBIL-style score between 300 and 900.
        annual_income: Applicant's declared annual income, in INR.
        loan_amount: Requested loan amount, in INR.
        tenure_months: Requested tenure, in months.
        has_defaults: Whether the credit report shows a prior default.

    Returns:
        A dict with risk_score, risk_band, and emi_to_income_ratio.
    """
    score = credit_score / 900 * 60
    if has_defaults:
        score -= 25
    monthly_income = annual_income / 12
    emi_estimate = loan_amount / tenure_months
    ratio = round(emi_estimate / monthly_income, 4) if monthly_income else 1.0
    score -= min(ratio * 40, 40)
    score = max(0, min(100, round(score, 1)))

    if score >= 70:
        band = "Low"
    elif score >= 40:
        band = "Medium"
    else:
        band = "High"

    return {"risk_score": score, "risk_band": band, "emi_to_income_ratio": ratio}
```

## Step 4: Define `risk_specialist_agent`, then serve it over A2A

Create `agents/lesson15a_a2a/risk_specialist/agent.py`

The agent itself is a plain definition, no A2A wiring in it at all:

```python
"""Lesson 15a: The risk specialist agent, plain definition, no A2A wiring.
"""

from google.adk.agents import Agent

from common.model_config import get_model
from risk_specialist.tools import calculate_risk_score

instruction = """You are a loan risk specialist. Given an applicant's
credit_score, annual_income, loan_amount, tenure_months, and
has_defaults, call `calculate_risk_score` with those five values and
report the risk_score, risk_band, and emi_to_income_ratio back.

Always call the tool. Never estimate the score yourself.
"""

risk_specialist_agent = Agent(
    name="risk_specialist_agent",
    model=get_model("primary"),
    description="Assesses loan risk given credit and applicant details, and returns a risk score and band.",
    instruction=instruction,
    tools=[calculate_risk_score],
)
```

To serve this agent over A2A protocol, we create a separate file `risk_service.py` one level above the `risk_specialist/` folder.

Create `agents/lesson15a_a2a/risk_service.py`

```python 
"""Lesson 15a: Serve risk_specialist_agent over A2A.

Run this file directly, it's a standalone server, not something
adk web or another agent's main.py imports.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))  # adds agents/ for common.*
sys.path.insert(0, str(THIS_DIR))  # adds this lesson's own folder for risk_specialist.*

from google.adk.a2a.utils.agent_to_a2a import to_a2a

from risk_specialist.agent import risk_specialist_agent

app = to_a2a(risk_specialist_agent, host="localhost", port=8001)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
```

Same split this series has used since Lesson 1, `agent.py` defines an agent, a separate file decides what to do with it. Here that separate file happens to start a server instead of driving a console loop.

> 📌 **NOTE:** Here's the actual Agent Card this exact agent serves. You can confirm this by running it and querying the live endpoint `http://localhost:8001/.well-known/agent-card.json`
>
> ```json
> {
>   "name": "risk_specialist_agent",
>   "description": "Assesses loan risk given credit and applicant details, and returns a risk score and band.",
>   "supportedInterfaces": [
>     {
>       "url": "http://localhost:8001",
>       "protocolBinding": "JSONRPC",
>       "protocolVersion": "1.0"
>     }
>   ],
>   "version": "0.0.1",
>   "capabilities": {
>     "streaming": false,
>     "pushNotifications": false
>   },
>   "defaultInputModes": ["text/plain"],
>   "defaultOutputModes": ["text/plain"],
>   "skills": [
>     {
>       "id": "risk_specialist_agent",
>       "name": "model",
>       "description": "Assesses loan risk given credit and applicant details, and returns a risk score and band. I am a loan risk specialist. Given an applicant's credit_score, annual_income, loan_amount, tenure_months, and has_defaults, call calculate_risk_score with those five values and report the risk_score, risk_band, and emi_to_income_ratio back. Always call the tool. Never estimate the score yourself.",
>       "tags": ["llm"]
>     },
>     {
>       "id": "risk_specialist_agent-calculate_risk_score",
>       "name": "calculate_risk_score",
>       "description": "Calculates a deterministic risk score for a loan application...",
>       "tags": ["llm", "tools"]
>     }
>   ]
> }
> ```


## Step 5: Consume it, two ways

Create `agents/lesson15a_a2a/loan_orchestrator/agent.py`

```python
"""Lesson 15a: Two ways of consuming the remote risk_specialist_agent.
"""

from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools.agent_tool import AgentTool

from common.model_config import get_model

# Same RemoteA2aAgent instance, two different roles below. The URL points
# at risk_service.py's own server, which must already be running,
# in a separate terminal, before either of these is used.
remote_risk_agent = RemoteA2aAgent(
    name="risk_assessment_agent",
    agent_card="http://127.0.0.1:8001/.well-known/agent-card.json",
)


# --- Pattern 1: AgentTool, for a model's own judgment call. ---

orchestrator_instruction = """You are a loan support assistant. When a
customer gives you enough detail for a full risk assessment, credit
score, annual income, loan amount, tenure, and default history, all
five, delegate to the risk assessment agent tool. For anything else,
including a request missing one of those five details, ask for what's
missing instead of guessing or calling the tool anyway.
"""

root_agent = Agent(
    name="loan_orchestrator",
    model=get_model("primary"),
    description="Loan support assistant that delegates full risk assessments to a remote A2A agent.",
    instruction=orchestrator_instruction,
    tools=[AgentTool(agent=remote_risk_agent)],
)


# --- Pattern 2: plain sub-agent, for a step that always runs. ---

intake_agent = Agent(
    name="intake_agent",
    model=get_model("primary"),
    description="Confirms an applicant's details are complete before risk assessment.",
    instruction="""Read the applicant's credit_score, annual_income,
loan_amount, tenure_months, and has_defaults from the user's message
and restate them plainly, so the next step has a clear record of what's
being assessed. Don't calculate anything yourself.
""",
)

loan_pipeline = SequentialAgent(
    name="loan_pipeline",
    sub_agents=[intake_agent, remote_risk_agent],
)
```

Same `remote_risk_agent`, used two different ways below it, and both construct without conflict, confirmed directly. Wrapped in `AgentTool`, it's a tool `loan_orchestrator`'s own model decides whether to call. Placed directly in `loan_pipeline`'s `sub_agents`, it's just a step that always runs, no decision involved, exactly the choice you'd make between these two patterns for any local agent.

## Step 6: Wire up main.py

Create `agents/lesson15a_a2a/main.py`

```python
"""Lesson 15a: Run both consuming patterns against the risk service.

Start risk_service.py first, in a separate terminal, before
running this.
"""

import asyncio
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))  # adds agents/ for common.*
sys.path.insert(0, str(THIS_DIR))  # adds this lesson's own folder for loan_orchestrator

from google.adk.sessions import InMemorySessionService

from common.runner_utils import run_agent_query
from loan_orchestrator.agent import loan_pipeline, root_agent

APP_NAME = "lesson15a_a2a"
USER_ID = "console_user"
QUERY = (
    "Full risk check please: credit score 773, annual income 900000, "
    "loan amount 500000, tenure 36 months, no prior defaults."
)


async def run_agent_tool_demo() -> None:
    """Runs the query against the AgentTool-based orchestrator."""
    print("=== Pattern 1: AgentTool (a model's own judgment call) ===\n")
    session_service = InMemorySessionService()
    response = await run_agent_query(
        agent=root_agent,
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=str(uuid.uuid4()),
        query=QUERY,
        session_service=session_service,
    )
    print("Response:", response)
    print()


async def run_sequential_demo() -> None:
    """Runs the same query through the fixed intake-then-assess pipeline."""
    print("=== Pattern 2: plain sub-agent in a fixed SequentialAgent pipeline ===\n")
    session_service = InMemorySessionService()
    response = await run_agent_query(
        agent=loan_pipeline,
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=str(uuid.uuid4()),
        query=QUERY,
        session_service=session_service,
    )
    print("Response:", response)
    print()


async def main() -> None:
    await run_agent_tool_demo()
    await run_sequential_demo()


if __name__ == "__main__":
    asyncio.run(main())
```

## Step 7: Run it, two terminals

In the first terminal, start the server:

```bash
cd adk2_tutorial
source .venv/bin/activate
cd agents/lesson15a_a2a
uv run risk_service.py
```

In the second, run the consuming side from the project root folder (`adk2_tutorial`)

```bash
source .venv/bin/activate
uv run agents/lesson15a_a2a/main.py
```

You should see both patterns reach the same real server and come back with the same risk assessment, a `risk_score`, `risk_band`, and `emi_to_income_ratio`, computed by `calculate_risk_score` running in the *other* process, not this one.

> 📌 **NOTE** You will see a lot of log messages from the ADK, which makes it difficult to pick out output from our program. To suppress these messages on the console, use the `PYTHONWARNINGS=ignore` technique we introduced back in Lesson 2.

## Step 8: See the raw task lifecycle

`RemoteA2aAgent` handles the entire task lifecycle from Lesson 15's theory for you, submitting a task, tracking its state, resolving the final result, none of it visible in the code you've written so far. This step skips `RemoteA2aAgent` entirely and talks to the server's own protocol endpoint directly, so you can see the actual task object underneath.

Create `agents/lesson15a_a2a/peek_raw_task.py`

```python
"""Lesson 15a: See the raw A2A task lifecycle underneath RemoteA2aAgent.

RemoteA2aAgent handles all of this for you, submitting a task, polling
it, resolving the final state. This script skips RemoteA2aAgent
entirely and talks to the server's own protocol endpoint directly, so
you can see the actual task object A2A passes around, not just the
final answer.

Start risk_service.py first, in a separate terminal, before
running this.
"""

import asyncio
import json

import httpx


async def main() -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8001/",
            json={
                "jsonrpc": "2.0",
                "id": "req-1",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": "credit score 773, annual income 900000, loan amount 500000, tenure 36 months, no defaults"}],
                        "messageId": "msg-1",
                    }
                },
            },
        )
        result = response.json()
        task = result["result"]
        print("Task ID:", task["id"])
        print("Task state:", task["status"]["state"])
        print()
        print("Full task object:")
        print(json.dumps(task, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
```

Run it in a separate terminal from the `adk2_tutorial` folder, with the server still running in its own terminal:

```bash
cd adk2_tutorial
source .venv/bin/activate
uv run agents/lesson15a_a2a/peek_raw_task.py
```

Here's the real output, no live API key available when this was run, which is exactly why this is a good demonstration, `FAILED` is one of the eight real states from Lesson 15, and this is what it actually looks like on the wire, not a description of it:

```
Task ID: bb807bbf-f49e-4a25-ab9e-156b1fa80dba
Task state: failed
```

The full task object underneath, also real output, shows exactly why: an `adk_error_code` of `TypeError`, and the actual authentication error message, sitting right inside `status.message`, the same place a successful run would put the real risk assessment instead. Run this yourself with a real API key configured, and `state` becomes `completed`, with the actual `risk_score`, `risk_band`, and `emi_to_income_ratio` in that same spot, `RemoteA2aAgent` is doing exactly this underneath every call you made in Step 7, just handling the state-checking and the final extraction for you.

## Try it in adk web too

```bash
adk web agents
```

Select `lesson15a_a2a.loan_orchestrator`. You'll also see `lesson15a_a2a.risk_specialist` listed, don't select that one, its `agent.py` deliberately has no `root_agent`, and it also imports itself as a package in a way `adk web`'s own loading doesn't resolve the same way `risk_service.py` does. Selecting it fails with a `ModuleNotFoundError`, confirmed directly, not the friendlier "no root_agent" message you'd get otherwise. It's meant to run standalone, through `risk_service.py`, the way Step 7 does.

## In this lesson

You built a real A2A server, `risk_specialist_agent`, the same one from 13a, wrapped in `to_a2a()` and run as its own process, its real Agent Card confirmed by actually querying it, not assumed from documentation. You consumed it two ways from a second process, `AgentTool` for a model's own delegation judgment, and a plain sub-agent in a `SequentialAgent` for a step that always runs, the same `RemoteA2aAgent` instance doing both jobs without conflict. Then you went underneath `RemoteA2aAgent` entirely, talking to the server's raw protocol endpoint directly, and saw a real task object with a real `state` field, `failed` in this run, one of the eight states Lesson 15's theory covered, no longer just a description of what happens, the actual thing. And you saw exactly where this pairing's verification reaches its real limit, the protocol mechanics confirmed directly, the final model reasoning depending on your own credentials.

## In the next lesson

The next lesson covers Graph-Based Workflows, ADK's `Workflow` class for routing and human-in-the-loop patterns beyond what `SequentialAgent`, `ParallelAgent`, and `LoopAgent` cover on their own.
