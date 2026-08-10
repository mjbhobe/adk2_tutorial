# Lesson 11d: AgentTool — Agents as Tools

`GoogleSearchTool` only works with a Gemini model, no exceptions, no flag to work around it. If your agent runs on another LLM, such as Claude, and you need Google Search alongside it, you're out of luck, unless you give the search step its own home, on its own model, and reach it the way you'd reach any other tool.

The same shape of problem shows up around configuration, not just models. Picture an agent that scores a loan's risk, which needs a low temperature so the same inputs produce the same score every time, and also drafts a short, warm note to go with the approval letter, which reads better with a higher temperature and more freedom in phrasing. Both live under one agent's generation config, so you can't give one a low temperature and the other a high one, whichever setting you pick applies to every turn that agent takes. Giving the note-writing step its own agent, with its own config, is the only way to let each task have the settings it actually needs. Generation config lives on the whole agent, not per tool call.

Then there's a genuinely different kind of problem, and it's the same limitation `SequentialAgent`, `ParallelAgent`, and `LoopAgent` all share: the shape of the pipeline is fixed before you run it, decided in code, ahead of time. None of them can decide, mid-run, that a customer message asking about a balance needs one specialist while a message reporting a stolen card needs a completely different one. `SequentialAgent` can't skip a step. `ParallelAgent` runs everything. `LoopAgent` repeats one thing. That kind of routing needs a model to decide, at the moment it matters, not a fixed sequence.

A few more reasons show up once you're building for real rather than for a lesson. Giving a specialist its own tool list, separate from your main agent's, keeps that specialist's internal retries and multiple tool calls out of your main agent's context, so it stays smaller and cleaner. Splitting fifteen tools across three specialists, each exposed as one callable unit, gives your top-level agent three choices instead of fifteen, and fewer choices means fewer wrong picks. An entire finished pipeline, like Lesson 11a's four-step loan underwriting flow, can be handed to something bigger as a single callable unit, without whatever's calling it needing to know it's actually four steps underneath. And an agent you didn't write yourself, something imported from elsewhere, or reached over the network through Lesson 15's A2A protocol, can be folded into your own workflow without touching its internals at all, your own agent captures its output on your own terms, through your own instruction and your own state, rather than modifying code you don't control.

Every one of these is a different problem. They all lead to the same answer: something that decides, or something you can't or won't modify, needs to be reachable the way a tool is reachable, called when it's actually needed, not wired into a fixed sequence ahead of time. That's what `AgentTool` is for.

## What this lesson builds

Two of these, chosen because they sit at opposite ends of "why": one is a hard constraint you can't avoid, the other is a judgment call only a model can make.

**Platform-forced**: a research agent that needs Google Search alongside its own reasoning, where the search step itself has to run on Gemini even though everything else in this series runs on Claude.

**Routing**: a customer support agent that has to decide, per message, whether a balance inquiry or a card block is what's actually being asked for, and call the right specialist, not both.

## How it works

```python
from google.adk.tools.agent_tool import AgentTool

root_agent = Agent(
    name="orchestrator",
    model=get_model("primary"),
    tools=[AgentTool(agent=some_specialist_agent)],
)
```

That's the whole mechanism. `some_specialist_agent` can be any agent, its own model, its own instruction, its own tools, completely independent of the orchestrator. Once wrapped, it shows up to the orchestrator's model as one more tool it can choose to call, with a description drawn from the specialist agent itself. Under the hood, `AgentTool` runs the wrapped agent in its own isolated sub-run, with its own session and its own model, only the final result comes back to the caller. That isolation is exactly why the wrapped agent's model never has to match the caller's.

Wrapping a whole existing pipeline works the same way, no different mechanism, just a different kind of agent going in:

```python
from google.adk.tools.agent_tool import AgentTool
from loan_pipeline.agent import root_agent as loan_underwriting_pipeline

underwriting_tool = AgentTool(agent=loan_underwriting_pipeline)
```

Three lines, and Lesson 11a's entire four-step pipeline becomes one tool call from something bigger.

None of this is the right call when the order or the branches are actually known in advance, that's still `SequentialAgent`, `ParallelAgent`, or `LoopAgent`. `AgentTool` earns its place specifically where something has to decide, or where you're working with an agent you don't control.

## Step 1: Set up the folder structure

Two independent examples this lesson, not one pipeline, so two folders side by side:

```
agents/lesson11d_agent_tool/
├── main.py
├── research_pipeline/
│   ├── __init__.py
│   ├── agent.py
│   └── sub_agents/
│       ├── __init__.py
│       └── search_specialist_agent/
│           ├── __init__.py
│           └── agent.py
└── support_pipeline/
    ├── __init__.py
    ├── agent.py
    └── sub_agents/
        ├── __init__.py
        ├── balance_inquiry_agent/
        │   ├── __init__.py
        │   ├── agent.py
        │   └── tools.py
        └── card_block_agent/
            ├── __init__.py
            ├── agent.py
            └── tools.py
```

`research_pipeline` is the platform-forced example. `support_pipeline` is the routing example. `search_specialist_agent` has no `tools.py`, its only tool is the built-in `GoogleSearchTool`, nothing custom to write.

## Step 2: Build the search specialist

Create `agents/lesson11d_agent_tool/research_pipeline/sub_agents/search_specialist_agent/agent.py`

```python
"""Lesson 11d: Search specialist agent, Gemini-only by platform requirement.

GoogleSearchTool only works with a Gemini model, and it can't share an
agent with any other tool. This agent exists purely to hold that one
tool in isolation; the orchestrator that actually talks to the user
stays on Claude and reaches this agent through an AgentTool.
"""

from google.adk.agents import Agent
from google.adk.tools import google_search

instruction = """You answer questions using Google Search. Search for
what's needed, then give a short, direct answer based on what you find.
"""

search_specialist_agent = Agent(
    name="search_specialist_agent",
    # GoogleSearch forces us to use Gemini model
    # model=Gemini(model="gemini-flash-latest"),
    model="gemini-3.5-flash-lite",
    description="Answers questions using Google Search.",
    instruction=instruction,
    tools=[google_search],
)
```

## Step 3: Build the research agent

Create `agents/lesson11d_agent_tool/research_pipeline/agent.py`

```python
"""Lesson 11d: Research agent, Claude, with a Gemini specialist wrapped as a tool.
"""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from common.model_config import get_model

from .sub_agents.search_specialist_agent.agent import search_specialist_agent

instruction = """You are a research assistant. When a question needs
current information you wouldn't already know, use the search tool to
find it, then answer based on what it returns.
"""

root_agent = Agent(
    name="research_agent",
    model=get_model("primary"), # Claude!
    description="Answers questions, using a Google Search specialist for anything needing current information.",
    instruction=instruction,
    # which can now use google_search 😌
    tools=[AgentTool(agent=search_specialist_agent)],
)
```

Our `root_agent` stays on Claude, which is our preferred model. It never touches `GoogleSearchTool` directly, from its point of view, it just has a tool called `search_specialist_agent` that happens to answer questions.

## Step 4: Build the two support specialists

Create tool for balance inquiry agent - `agents/lesson11d_agent_tool/support_pipeline/sub_agents/balance_inquiry_agent/tools.py`

```python
"""Lesson 11d: Tools for the balance inquiry agent.
"""

import hashlib


def get_account_balance(account_number: str) -> dict:
    """Fetches a mock account balance.

    Deterministic hash of the account number, so the same account
    always shows the same balance.

    Args:
        account_number: The customer's account number.

    Returns:
        A dict with:
            account_number (str): The account that was checked.
            balance (float): The current balance, in INR.
    """
    digest = hashlib.sha256(account_number.encode()).hexdigest()
    seed = int(digest[:8], 16)
    return {"account_number": account_number, "balance": float(seed % 500000)}
```

Create the balance inquiry agent - `agents/lesson11d_agent_tool/support_pipeline/sub_agents/balance_inquiry_agent/agent.py`

```python
"""Lesson 11d: Balance inquiry agent, one of two specialists behind the router.
"""

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import get_account_balance

instruction = """Extract the account_number from the request and call
`get_account_balance` with it. Report the balance back in one sentence.
"""

balance_inquiry_agent = Agent(
    name="balance_inquiry_agent",
    model=get_model("primary"),
    description="Looks up a customer's current account balance.",
    instruction=instruction,
    tools=[get_account_balance],
)
```

Create tool for card block agent - `agents/lesson11d_agent_tool/support_pipeline/sub_agents/card_block_agent/tools.py`

```python
"""Lesson 11d: Tools for the card block agent.
"""


def block_card(card_number: str, reason: str) -> dict:
    """Blocks a debit or credit card.

    A mock action, no real card network involved. Always succeeds.

    Args:
        card_number: The card number to block.
        reason: Why the card is being blocked, e.g. "lost" or "stolen".

    Returns:
        A dict with:
            card_number (str): The card that was blocked.
            reason (str): The reason given.
            status (str): Always "blocked" in this mock.
    """
    return {"card_number": card_number, "reason": reason, "status": "blocked"}
```

Create the card block agent - `agents/lesson11d_agent_tool/support_pipeline/sub_agents/card_block_agent/agent.py`

```python
"""Lesson 11d: Card block agent, the other specialist behind the router.
"""

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import block_card

instruction = """Extract the card_number and the reason (lost or
stolen) from the request and call `block_card` with them. Confirm the
block back in one sentence.
"""

card_block_agent = Agent(
    name="card_block_agent",
    model=get_model("primary"),
    description="Blocks a customer's lost or stolen card.",
    instruction=instruction,
    tools=[block_card],
)
```

Nothing new in either of these on their own, they're the same shape as any single-tool agent from earlier lessons. What matters is what happens next.

## Step 5: Build the router

This is a very simple router, which supports only balance inquiry & card-blocking requests. Depending on the request (in text) coming into this agent, it uses its `AgentTool` tools to route to the correct sub-agent that can handle the request.

Create `agents/lesson11d_agent_tool/support_pipeline/agent.py`

```python
"""Lesson 11d: Customer support agent, routes between two specialists at runtime.
"""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from common.model_config import get_model

from .sub_agents.balance_inquiry_agent.agent import balance_inquiry_agent
from .sub_agents.card_block_agent.agent import card_block_agent

instruction = """You handle customer banking requests.

If the customer wants to know their balance, use the balance inquiry
tool. If the customer reports a lost or stolen card, use the card
block tool. Use whichever one actually applies to what they asked,
not both.
"""

root_agent = Agent(
    name="customer_support_agent",
    model=get_model("primary"),
    description="Routes customer banking requests to the right specialist.",
    instruction=instruction,
    tools=[
        # balance inquiry handled by balance inquiry Agent masquerading as a tool
        AgentTool(agent=balance_inquiry_agent),
        # card blocks handled by card block Agent masquerading as a tool
        AgentTool(agent=card_block_agent),
    ],
)
```

Two `AgentTool`s in one list. Compare this to `disbursement_agent` and `referral_agent` from Lesson 12: those two both ran on every single application, each one checking whether it applied and doing nothing if not. Here, only one specialist ever actually runs, the model picks based on what the customer actually said. That's the real difference `AgentTool` makes available, a genuine choice, not a fixed sequence with self-checks bolted on.

## Step 6: Wire up main.py

Create `agents/lesson11d_agent_tool/main.py`

```python
"""Lesson 11d: Run both AgentTool examples.
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
from research_pipeline.agent import root_agent as research_agent
from support_pipeline.agent import root_agent as support_agent

RESEARCH_APP = "lesson11d_research"
SUPPORT_APP = "lesson11d_support"
USER_ID = "console_user"


async def run_research_demo() -> None:
    """Runs one fixed query through the Gemini-backed search specialist, via AgentTool."""
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())
    query = "What's today's date, and who is the current Prime Minister of India?"

    print("=== Example 1: platform-forced (Gemini search specialist) ===")
    print(f"Query: {query}\n")

    response = await run_agent_query(
        agent=research_agent,
        app_name=RESEARCH_APP,
        user_id=USER_ID,
        session_id=session_id,
        query=query,
        session_service=session_service,
    )
    print("Response:", response)
    print()


async def run_support_loop() -> None:
    """Runs an interactive loop against the routing customer support agent."""
    session_service = InMemorySessionService()

    print("=== Example 2: routing (customer support agent) ===")
    print("Ask about a balance, or report a lost/stolen card. Type 'quit' to exit.\n")

    loop = asyncio.get_event_loop()
    while True:
        try:
            user_input = await loop.run_in_executor(None, lambda: input("You: "))
        except EOFError:
            break

        if user_input.strip().lower() in ("quit", "exit"):
            break

        session_id = str(uuid.uuid4())
        response = await run_agent_query(
            agent=support_agent,
            app_name=SUPPORT_APP,
            user_id=USER_ID,
            session_id=session_id,
            query=user_input,
            session_service=session_service,
        )
        print("Agent:", response, "\n")


async def main() -> None:
    await run_research_demo()
    await run_support_loop()


if __name__ == "__main__":
    asyncio.run(main())
```

## Step 7: Run it

Run the following commands from the project root (`adk2_tutorial`) in a new terminal.

```bash
source .venv/bin/activate
uv run agents/lesson11d_agent_tool/main.py
```

The research demo runs first, one fixed query, showing `research_agent` (Claude) reach into `search_specialist_agent` (Gemini) through the `AgentTool` and come back with a current answer. Then the interactive loop starts. Try:

```
You: What's the balance on account ACC998877?
```

The balance specialist should get called, not the card one. Then, in a fresh prompt:

```
You: My card 4111222233334444 was stolen, please block it.
```

This time the card specialist should get called instead. Same orchestrator, same two tools available every time, different tool chosen depending on what you actually said.

## Try it in adk web too

```bash
adk web agents
```

Both `lesson11d_agent_tool.research_pipeline` and `lesson11d_agent_tool.support_pipeline` show up separately. Selecting `support_pipeline` and watching the trace is the clearer of the two: send a balance question, look at the trace, then send a card question in a new session and compare. You'll see a different specialist agent's name appear in the trace each time, driven entirely by what you typed.

## If you're coming from LangChain or LangGraph

This maps closely to what LangChain calls tool-calling agents with sub-agents as tools, or in LangGraph terms, a supervisor node that routes to worker nodes based on the model's own output rather than a fixed edge. The idea is common across every agent framework for exactly the reason it shows up here: some routing decisions can't be known ahead of time, so something has to make the call at runtime, and a model is the natural thing to make it.

## In this lesson

You used `AgentTool` for two different reasons. The Gemini search specialist showed the forced case, a tool with its own model and isolation requirement, solved by giving it its own single-purpose agent and exposing that agent as a tool to the Claude-based orchestrator that actually talks to the user. The customer support router showed the case `SequentialAgent`, `ParallelAgent`, and `LoopAgent` genuinely can't cover: a decision that depends on what the request says, made by the model at the moment it matters, not fixed in code ahead of time.

## In the next lesson

The next lesson covers Skills, packaging the tool logic you've now written several times, PAN validation, credit bureau mocks, EMI calculations, into reusable bundles agents can share, rather than copying the same `tools.py` patterns into every new lesson's folder.
