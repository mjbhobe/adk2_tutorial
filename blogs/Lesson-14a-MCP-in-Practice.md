# Lesson 14a: MCP Servers in Practice

MCP (Model Context Protocol) is an open protocol for connecting an agent to tools and data that live outside your own process, possibly in a separate server built by a different team, which you connect to over a standardized interface. An MCP server exposes tools, and sometimes resources. An MCP client, `McpToolset` in ADK's case, connects to a server and makes its tools available to your agent the same way any local tool would be. Everything you've built so far lived inside your own Python process, this is the first time an agent reaches something genuinely external, a real, live service you don't control and didn't write.

Stripe (`stripe.com`) is a payments and financial infrastructure platform, used by real businesses to accept payments, manage subscriptions, issue invoices, and handle refunds. It's a genuine market infrastructure, not a demo service built for tutorials. To use it, you'll need to create a Stripe account fore free. Every Stripe account starts in test mode, where test API keys (prefixed `sk_test_`, or `rk_test_` for a restricted key) work against the full API without processing any real money or charging anything. That test mode is exactly what this lesson uses, no real charges, no real refunds, nothing that costs money or touches an actual customer.

## What we're going to be building

Picture a customer support desk that needs two different levels of access to the same payment system (Stripe in our case). Most of the time the helpdesk person just wants to look something up, account details, recent activity etc. - nothing that changes anything. However, some types of requests, such as a valid refund request, requires a modification to be made with a valid stated reason. This lesson builds both types of requests against the Strips MCP server: an assistant that can freely check account information, and a separate assistant that only gains the ability to issue a refund once it's actually decided that's what the situation calls for.

Concretely that translates to two agents running against the same [Stripe's official MCP server](https://mcp.stripe.com). The first is a plain consumer, which has access to every Stripe tool available directly. The second request pairs MCP with Skills, which we covered in Lesson 13. Specifically, we deevelop a `refund-processing` skill that keeps exactly one tool, `create_refund`, hidden from the agent until the model decides that skill actually applies, only then does that tool become callable.

> 📌 **NOTE:** Stripe's MCP server normally connects through OAuth, an interactive browser authorization step. Stripe's own documentation carves out a specific exception for access from AI agents. For such cases _you can pass a Stripe API key as a bearer token to the MCP remote server_.That's what we'll use, a static `Authorization: Bearer` header, no browser step, which complicates access for simple console applications - the kind we'll be building.

## Step 1: Set up the folder structure

This is the folder structure we'll be building out for this application.

```
agents/lesson14a_mcp/
├── main.py
└── mcp_demo/
    ├── __init__.py
    ├── agent.py
    └── skills/
        └── refund-processing/
            └── SKILL.md
```

In this application, we define 2 ADK agents inside the same `agent.py` file, which is an exception from the convention we have been following so far. This is ok for small apps like ours, but should be avoided for production code.

## Step 2: Write the skill with the `create_refund` tool

Create `agents/lesson14a_mcp/mcp_demo/skills/refund-processing/SKILL.md`

```markdown
---
name: refund-processing
description: |
  Issues a refund for a Stripe charge or payment intent. Use this only
  when a customer request clearly warrants a refund, never issue one
  speculatively or without a stated reason.
metadata:
  adk_additional_tools:
    - create_refund
---

# Refund Processing

Refunds are irreversible once processed. Before calling `create_refund`:

1. Confirm you have the charge ID or payment intent ID to refund, not
   just a customer name or email, ask for it if it's missing.
2. Confirm the reason for the refund is stated, duplicate charge,
   fraudulent, or requested by customer.
3. Call `create_refund` with the charge or payment intent ID.
4. Report the refund ID and status back plainly, don't editorialize.

Never call `create_refund` speculatively "just in case." If the request
is ambiguous, ask for clarification instead of guessing.
```

There are several tools that Stripe's MCP server exposes: `create_refund`, `stripe_api_read`, `stripe_api_write`, `get_stripe_account_info`etc. However `create_refund` is the only one our skill needs, so it is the only one named by `adk_additional_tools` in the `SKILL.md` file. All othe tools are out of reach, unless some other skill names them specifically.

## Step 3: Build the agents

As stated before, we make an exception in this lesson and code both the agents in 1 Python file. Create `agents/lesson14a_mcp/mcp_demo/agent.py`

```python
"""Lesson 14a: Two agents, one plain MCP consumer, one skill-gated.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# get a free API key by registering yourself on stripe.com
# save the API key to your .env file as with key STRIPE_SECRET_KEY 

load_dotenv(override=True)

from google.adk.agents import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.adk.tools.skill_toolset import SkillToolset

from common.model_config import get_model

STRIPE_SECRET_KEY = os.environ["STRIPE_SECRET_KEY"]

SKILLS_DIR = Path(__file__).resolve().parent / "skills"
refund_processing_skill = load_skill_from_dir(SKILLS_DIR / "refund-processing")


def _make_stripe_mcp_toolset() -> McpToolset:
    """Builds a fresh McpToolset pointed at Stripe's official remote MCP server.

    A new instance per agent, not a shared one, since each McpToolset
    owns its own underlying MCP session lifecycle.

    Returns:
        An McpToolset connected to https://mcp.stripe.com, authenticated
        with a bearer token, the documented approach for autonomous
        agents rather than the interactive OAuth flow.
    """
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="https://mcp.stripe.com",
            headers={"Authorization": f"Bearer {STRIPE_SECRET_KEY}"},
        ),
    )


# --- Plain consuming agent: every Stripe tool is always available. ---

research_instruction = """You are a Stripe account research assistant.
You have direct access to Stripe's MCP server. Use `get_stripe_account_info`,
`stripe_api_read`, or `stripe_api_search` as needed to answer questions
about the account, customers, charges, or other Stripe data.

Never call `stripe_api_write` or `create_refund`, this agent only reads
data, it doesn't change anything.
"""

stripe_research_agent = Agent(
    name="stripe_research_agent",
    model=get_model("primary"),   # Claude Haiku
    description="Answers questions about Stripe account data using every available Stripe MCP tool directly.",
    instruction=research_instruction,
    # all available tools
    tools=[_make_stripe_mcp_toolset()],
)


# --- Skill-gated agent: create_refund only appears once the skill loads. ---

refund_instruction = """You are a customer support assistant who can
issue refunds through Stripe when genuinely warranted. Refund handling
is not something you know how to do by default, load the
refund-processing skill first, follow its instructions exactly, and
only then decide whether to actually issue one.
"""

stripe_refund_agent = Agent(
    name="stripe_refund_agent",
    model=get_model("primary"),
    description="Handles customer refund requests, loading refund-processing guidance and the refund tool only when needed.",
    instruction=refund_instruction,
    tools=[
        SkillToolset(
            skills=[refund_processing_skill],
            additional_tools=[_make_stripe_mcp_toolset()],
        ),
    ],
)

# adk web / adk run look for a variable named root_agent.
root_agent = stripe_research_agent
```

Notice `agent.py` calls `load_dotenv(override=True)` itself, right at the top, rather than relying on `main.py` to have done it first. That matters here specifically: `adk web` imports `agent.py` directly, it never runs `main.py` at all, so if the `.env` loading only happened in `main.py`, `STRIPE_SECRET_KEY` would be missing and this agent would fail to construct the moment you tried to select it in `adk web`. Calling `load_dotenv()` again in `main.py` afterward is harmless, it just re-reads the same file.

Two completely different wiring shapes for the same underlying server. `stripe_research_agent` gets the `McpToolset` bare, in `tools=[]`, every Stripe tool the server offers becomes callable immediately. `stripe_refund_agent` gets the *exact same kind* of `McpToolset`, but only as `additional_tools` on a `SkillToolset`, meaning none of Stripe's tools are visible at all until the model decides `refund-processing` is relevant and loads it, and even then, only `create_refund` shows up, not the rest of the server's surface.

## Step 4: Wire up main.py

Create our console based driver program `agents/lesson14a_mcp/main.py`

```python
"""Lesson 14a: Run both Stripe MCP agents.
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
from mcp_demo.agent import stripe_refund_agent, stripe_research_agent

RESEARCH_APP = "lesson14a_stripe_research"
REFUND_APP = "lesson14a_stripe_refund"
USER_ID = "console_user"


async def run_research_demo() -> None:
    """Runs one fixed query through the plain, always-available Stripe MCP agent."""
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())
    query = "What's the current Stripe account information for this account?"

    print("=== Example 1: plain consuming (every Stripe tool always available) ===")
    print(f"Query: {query}\n")

    response = await run_agent_query(
        agent=stripe_research_agent,
        app_name=RESEARCH_APP,
        user_id=USER_ID,
        session_id=session_id,
        query=query,
        session_service=session_service,
    )
    print("Response:", response)
    print()


async def run_refund_loop() -> None:
    """Runs an interactive loop against the skill-gated refund agent."""
    session_service = InMemorySessionService()

    print("=== Example 2: skill-gated (create_refund only appears once loaded) ===")
    print("Try a refund request with a charge ID and a reason. Type 'quit' to exit.\n")

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
            agent=stripe_refund_agent,
            app_name=REFUND_APP,
            user_id=USER_ID,
            session_id=session_id,
            query=user_input,
            session_service=session_service,
        )
        print("Agent:", response, "\n")


async def main() -> None:
    await run_research_demo()
    await run_refund_loop()


if __name__ == "__main__":
    asyncio.run(main())
```

## Step 5: Set up your Stripe key and run it

Get a **restricted API key** from your Stripe Dashboard, not your full secret key, restricted keys let you grant only the specific permissions this agent actually needs, refunds and read access, nothing more. Add it to your `.env`:

```
STRIPE_SECRET_KEY=rk_test_...
```

Then:

```bash
uv run agents/lesson14a_mcp/main.py
```

The research demo runs first, asking for account information through the plain, always-available connection. Then the refund loop starts. Try:

```
You: I need to refund charge ch_xxxxx, the customer was charged twice by mistake.
```

The agent should load `refund-processing` before doing anything, then call `create_refund`. Try a vague one too:

```
You: Can you refund something for me?
```

Per the skill's own instructions, this should get a clarifying question back, not a guessed refund.

## Try it in adk web too

```bash
adk web agents
```

Select `lesson14a_mcp.mcp_demo`, which loads `stripe_research_agent` as `root_agent`. Send the account info query and watch the trace show a real MCP tool call, `get_stripe_account_info`, going out to an actual external server, not a mock.

## If you're coming from LangChain or LangGraph

LangChain has its own MCP adapter (`langchain-mcp-adapters`) that does roughly the same job as `McpToolset`, converting a remote server's tools into objects the framework's agents can call. The gating pattern, an MCP-backed tool only appearing once something decides it's relevant, isn't something either framework standardizes the way ADK's Skills system does here; in LangGraph you'd typically build that conditional exposure yourself, as part of your graph's routing logic, rather than getting it from a `metadata` field on a skill file.

## In this lesson

You connected an agent to a real, external, officially maintained MCP server for the first time in this series, Stripe's, over `StreamableHTTPConnectionParams`, authenticated the way Stripe documents for autonomous agents specifically, a bearer token, not the interactive OAuth flow. You saw the same server wired two different ways: bare in `tools=[]`, every tool always available, and gated behind a skill, one specific tool, `create_refund`, invisible until the model decides it's needed, verified structurally by confirming a stand-in multi-tool toolset filters down to exactly the named tool once its skill activates.

## In the next lesson

`14b` builds a server of your own, a mutual fund NAV lookup using the standalone `mcp` SDK, offered over both `StdioConnectionParams` and `StreamableHTTPConnectionParams`, then consumed back through `McpToolset` to prove the round trip actually works.
