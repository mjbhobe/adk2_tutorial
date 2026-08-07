# Lesson 11d: AgentTool — Agents as Tools

`SequentialAgent`, `ParallelAgent`, and `LoopAgent` all share one thing: the shape of the pipeline is fixed before you run it. You decide the order, or the branches, or the retry logic, in code, ahead of time. This lesson covers the one workflow mechanism where that's not true: `AgentTool`, which lets an agent's own model decide, at runtime, whether and which other agent to call.

## The problem we're solving

Two separate situations, both real, that none of the last three lessons can handle.

**First**: some tools have requirements that clash with the rest of your agent. `GoogleSearchTool` only works with a Gemini model, and it can't share an agent with any other tool at all, that's a hard platform rule, not a style choice. If your agent is built on Claude and also needs one other tool, you can't just add `GoogleSearchTool` to the list.

**Second**: sometimes which specialist should handle a request depends on what the request actually says, and you don't know that in advance. A customer support message asking about their balance needs one specialist; a message reporting a stolen card needs a completely different one. There's no fixed order here, no "always run both", it's a judgment call, and only a model can make it.

`AgentTool` solves both: it wraps a whole agent so it can be added to another agent's `tools` list, exactly like a Python function would be. The calling agent's model decides when to call it, the same way it decides when to call any other tool.

## How it works

```python
from google.adk.tools.agent_tool import AgentTool

root_agent = Agent(
    name="orchestrator",
    model=get_model("primary"),
    tools=[AgentTool(agent=some_specialist_agent)],
)
```

That's the whole mechanism. `some_specialist_agent` can be any agent, its own model, its own instruction, its own tools, completely independent of the orchestrator. Once wrapped, it shows up to the orchestrator's model as one more tool it can choose to call, with a description drawn from the specialist agent itself.

> **NOTE:** `AgentTool` isn't deprecated, unlike `SequentialAgent`, `ParallelAgent`, and `LoopAgent`. It's a separate, still-current mechanism. ADK does offer a newer, shorter way to write the same thing, setting `mode="single_turn"` on the specialist and adding it to the orchestrator's `sub_agents` list instead of `tools`, and letting ADK wrap it automatically. Under the hood that's the same `AgentTool` machinery, just less to type. This lesson uses the explicit form because it's clearer about what's actually happening.

## When to reach for it, and when not to

Two situations force your hand:

- **A built-in tool needs a different model, or can't share an agent with anything else.** `GoogleSearchTool` is this lesson's example, but the shape generalizes to any tool with its own model or isolation requirement.
- **A sub-task genuinely needs different generation settings than the rest of the agent**, a different temperature, a different safety configuration, something that lives on the agent as a whole, not per tool call.

A few more situations don't force you into it, but make it the right call:

- **Routing that has to be decided by a model**, this lesson's second example, and the one that doesn't fit `SequentialAgent`, `ParallelAgent`, or `LoopAgent` at all.
- **Keeping a specialist's internal back-and-forth out of the caller's context.** Whatever the specialist does internally, retries, several tool calls, stays inside its own turn. The caller just sees one tool call and one result.
- **Cutting down how many tools one agent has to choose between.** Grouping many tools into a few specialist agents, each exposed as one `AgentTool`, gives the top-level agent fewer, clearer choices.
- **Reuse across agents that aren't part of the same pipeline.** A `SequentialAgent`'s sub-agents can only belong to one parent. An `AgentTool` doesn't have that restriction, several unrelated orchestrators can each wrap the same specialist behavior independently.
- **Treating an entire existing pipeline as one callable unit.** You can wrap a whole `SequentialAgent` in an `AgentTool` just as easily as a single `Agent`:

```python
from google.adk.tools.agent_tool import AgentTool
from loan_pipeline.agent import root_agent as loan_underwriting_pipeline

underwriting_tool = AgentTool(agent=loan_underwriting_pipeline)
```

Three lines, and Lesson 11a's entire four-step pipeline becomes one tool call from something bigger.

None of this is the right call when the order or the branches are actually known in advance, that's still `SequentialAgent`, `ParallelAgent`, or `LoopAgent`. `AgentTool` earns its place specifically where a model has to decide.

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

```python
# agents/lesson11d_agent_tool/research_pipeline/sub_agents/search_specialist_agent/agent.py
"""Lesson 11d: Search specialist agent, Gemini-only by platform requirement.

GoogleSearchTool only works with a Gemini model, and it can't share an
agent with any other tool. This agent exists purely to hold that one
tool in isolation; the orchestrator that actually talks to the user
stays on Claude and reaches this agent through an AgentTool.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools.google_search_tool import GoogleSearchTool

instruction = """You answer questions using Google Search. Search for
what's needed, then give a short, direct answer based on what you find.
"""

search_specialist_agent = Agent(
    name="search_specialist_agent",
    # The one place in this series' policy that calls for Gemini: a
    # built-in tool that requires it. Everything else stays on Claude.
    model=Gemini(model="gemini-flash-latest"),
    description="Answers questions using Google Search. Requires Gemini; cannot hold any other tool.",
    instruction=instruction,
    tools=[GoogleSearchTool()],
)
```

This agent does exactly one thing and holds exactly one tool. That's not a stylistic choice, it's the constraint `GoogleSearchTool` imposes: one tool, one model, nothing else in the list.

## Step 3: Build the research agent

```python
# agents/lesson11d_agent_tool/research_pipeline/agent.py
"""Lesson 11d: Research agent, Claude, with a Gemini specialist wrapped as a tool.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
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
    model=get_model("primary"),
    description="Answers questions, using a Google Search specialist for anything needing current information.",
    instruction=instruction,
    tools=[AgentTool(agent=search_specialist_agent)],
)
```

`root_agent` stays on Claude, the model this whole series defaults to. It never touches `GoogleSearchTool` directly, from its point of view, it just has a tool called `search_specialist_agent` that happens to answer questions.

## Step 4: Build the two support specialists

```python
# agents/lesson11d_agent_tool/support_pipeline/sub_agents/balance_inquiry_agent/tools.py
"""Lesson 11d: Tools for the balance inquiry agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
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

```python
# agents/lesson11d_agent_tool/support_pipeline/sub_agents/balance_inquiry_agent/agent.py
"""Lesson 11d: Balance inquiry agent, one of two specialists behind the router.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
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

```python
# agents/lesson11d_agent_tool/support_pipeline/sub_agents/card_block_agent/tools.py
"""Lesson 11d: Tools for the card block agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
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

```python
# agents/lesson11d_agent_tool/support_pipeline/sub_agents/card_block_agent/agent.py
"""Lesson 11d: Card block agent, the other specialist behind the router.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
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

```python
# agents/lesson11d_agent_tool/support_pipeline/agent.py
"""Lesson 11d: Customer support agent, routes between two specialists at runtime.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
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
        AgentTool(agent=balance_inquiry_agent),
        AgentTool(agent=card_block_agent),
    ],
)
```

Two `AgentTool`s in one list. Compare this to `disbursement_agent` and `referral_agent` from Lesson 12: those two both ran on every single application, each one checking whether it applied and doing nothing if not. Here, only one specialist ever actually runs, the model picks based on what the customer actually said. That's the real difference `AgentTool` makes available, a genuine choice, not a fixed sequence with self-checks bolted on.

## Step 6: Wire up main.py

```python
# agents/lesson11d_agent_tool/main.py
"""Lesson 11d: Run both AgentTool examples.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
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

```bash
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

> **NOTE:** Earlier in this lesson, the `mode="single_turn"` shorthand was mentioned as a shorter way to write what `AgentTool` does explicitly. Worth being precise about what that is and isn't: it's unrelated to ADK's graph-based `Workflow` class, covered later in this series. Same field name, `mode`, different purpose, `single_turn` wraps an agent as a tool, exactly what this lesson built by hand. `Workflow` is a separate, larger orchestration primitive with its own reasons to exist.

## In this lesson

You used `AgentTool` for two different reasons. The Gemini search specialist showed the forced case, a tool with its own model and isolation requirement, solved by giving it its own single-purpose agent and exposing that agent as a tool to the Claude-based orchestrator that actually talks to the user. The customer support router showed the case `SequentialAgent`, `ParallelAgent`, and `LoopAgent` genuinely can't cover: a decision that depends on what the request says, made by the model at the moment it matters, not fixed in code ahead of time.

## In the next lesson

The next lesson covers Skills, packaging the tool logic you've now written several times, PAN validation, credit bureau mocks, EMI calculations, into reusable bundles agents can share, rather than copying the same `tools.py` patterns into every new lesson's folder.
