# Lesson 7a: Callbacks in Practice

Lesson 7 gave you the full theory: what each of the six callback points is, when it fires, and what kind of work belongs at each one. This lesson puts all six to work in a single cohesive application, so you can see them operating together rather than as six isolated features.

## Quick recap: the six callbacks and their purpose

Before we write a line of code, here's the compact version of everything from Lesson 7:

| Callback | Fires | Can short-circuit? | What it's for |
|---|---|---|---|
| `before_agent_callback` | Once per turn, before anything | Yes, if it returns `Content` | Access control, session bookkeeping |
| `before_model_callback` | Once per model call (multiple per turn if tools are used) | Yes, if it returns `LlmResponse` | Inject live context, compliance guards, caching |
| `after_model_callback` | Once per model call (multiple per turn if tools are used) | Yes, if it returns `LlmResponse` | Scan/filter model output, response enrichment |
| `before_tool_callback` | Once per tool call | Yes, if it returns `dict` | Validate args, log audit trail, mock in tests |
| `after_tool_callback` | Once per tool call | Yes, if it returns a `dict` | Redact PII, validate results, normalise errors |
| `after_agent_callback` | Once per turn, after everything | Yes, if it returns `Content` | Save to long-term memory, final response transform |

For all callbacks, returning `None` from the callback function is a signal to ADK to proceed normally (i.e. not short-circuit the turn).

And the critical constraint worth repeating before any code appears: **ADK calls your callback functions using keyword arguments**, matching your parameter names exactly. Get the name wrong, and you'll get a `TypeError` at runtime, not at import time, so the error only appears when a turn actually fires. The confirmed exact parameter names (verified from ADK's source) are:

- `before_agent_callback`: `callback_context`
- `after_agent_callback`: `callback_context`
- `before_model_callback`: `callback_context`, `llm_request`
- `after_model_callback`: `callback_context`, `llm_response`
- `before_tool_callback`: `tool`, `args`, `tool_context`
- `after_tool_callback`: `tool`, `args`, `tool_context`, `tool_response`

We'll call this out again at each callback as we write it.

## The application we're building: a wealth management advisory agent

A private wealth management desk serves customers across multiple account tiers: Standard, Gold, and Platinum. The agent we're building acts as a front-line advisor that can pull a customer's portfolio summary and current market index levels on demand. But unlike the simple agents in earlier lessons, this one has compliance and audit requirements around it:

- **Access control**: only recognised tier levels can get through. Anything else gets a polite block before the model is even called.
- **Turn tracking**: every turn is counted in session state, regardless of what the customer said.
- **Live market context**: before the model call, inject the latest market indices into the prompt dynamically, so the model's responses are always grounded in current data.
- **Compliance scanning**: after the model responds, scan for any language that resembles specific investment advice ("buy X", "sell Y"), since the agent is not licensed to give investment recommendations.
- **Audit logging**: before every tool call, log which tool was called and with what arguments, for the regulatory audit trail.
- **Result validation**: after every tool call, validate that the returned data is within expected ranges.
- **Memory**: after every turn, save the conversation to long-term memory so future sessions can recall what this customer discussed.

Six real jobs, six callbacks, one agent.

> 📌 **NOTE:** this application does not mimic a _real_ production implementation!
> 
> A modern Wealth Management Advisory (WMA) firm relies on a specialized technology ecosystem—often referred to as the **"Wealth Tech Stack"** (WTA) to handle everything from relationship management to complex trade executions and compliance. 
>
> Some common platforms that comprise the WTA are:
> * A Customer Relationship Management (CRM) platform
> * A Portfolio Management & Accounting System (PMS)
> * Financial Planning & Scenario Modeling Software
> * Order Management & Trading Systems (OMS) / Rebalancing Systems
> * Document Management Systems etc.
>
> A real agent running in a WTA environment would be expected to interface with one or more of these systems to fetch data. We are certainly not doing that 😁 - most of our data is mock-data. Our intention is to show you callbacks, not how to interface with live production systems!
><br/><br/>


## Step 1: Create the folder structure

From the root folder, run the following commands.

```bash
mkdir -p agents/lesson07a_callbacks/wealth_advisor
```

Following the convention established in Lesson 6a, `main.py` sits inside the lesson folder alongside the agent subfolder. Inside `agents/lesson07a_callbacks/wealth_advisor/` we now have four files: `tools.py` (the tool functions), `callbacks.py` (all six callback implementations), `agent.py` (the agent declaration), and `__init__.py`. 

## Step 2: Write the tools

Create `agents/lesson07a_callbacks/wealth_advisor/tools.py`:

```python
"""Lesson 7a: Callbacks in Practice.

Tool functions for the wealth management advisory agent. These are
plain Python functions with no ADK dependency, exactly like every
tool in this series, kept separate from agent.py so they can be
read, tested, and reasoned about independently.
"""


def get_portfolio_summary(customer_id: str) -> dict:
    """Returns a portfolio summary for the given customer.

    In a real system this would query the bank's portfolio management
    platform. Here we return realistic mock data so the lesson works
    without any external dependencies.

    Args:
        customer_id: The bank's unique identifier for this customer.

    Returns:
        A dict with total portfolio value, currency, and allocation
        breakdown across asset classes.
    """
    portfolios = {
        "CUST001": {
            "customer_id": "CUST001",
            "total_value": 12500000,
            "currency": "INR",
            "segments": {"equity": 60, "debt": 30, "liquid": 10},
        },
        "CUST002": {
            "customer_id": "CUST002",
            "total_value": 4200000,
            "currency": "INR",
            "segments": {"equity": 45, "debt": 45, "liquid": 10},
        },
    }
    return portfolios.get(
        customer_id,
        {
            "found": False,
            "customer_id": customer_id,
            "error": "Customer ID not found in portfolio system.",
        },
    )


def get_market_indices(markets: str = "IN,US,EU") -> dict:
    """Returns current market index levels for the requested markets.

    Fetches live closing prices from Yahoo Finance using index ticker
    symbols. Falls back to a clear error message per index if a fetch
    fails, rather than crashing the whole tool call.

    Args:
        markets: Comma-separated market codes. Supported: IN, US, EU.
            Defaults to all three.

    Returns:
        A dict of index names to their latest closing levels, plus a
        status field indicating whether markets are currently open.
    """
    import yfinance as yf

    index_map = {
        "IN": {"BSE_SENSEX": "^BSESN", "NSE_NIFTY50": "^NSEI"},
        "US": {"SP500": "^GSPC", "NASDAQ": "^IXIC"},
        "EU": {"FTSE100": "^FTSE", "DAX": "^GDAXI"},
    }

    result = {}
    for code in markets.split(","):
        code = code.strip().upper()
        if code not in index_map:
            result[code] = "Unknown market code"
            continue
        for name, ticker_symbol in index_map[code].items():
            try:
                ticker = yf.Ticker(ticker_symbol)
                hist = ticker.history(period="2d")
                if hist.empty:
                    result[name] = "No data available"
                else:
                    result[name] = round(float(hist["Close"].iloc[-1]), 2)
            except Exception as e:
                result[name] = f"Fetch error: {str(e)}"

    result["status"] = "live_data"
    return result
```

**NOTE:**

* We are mocking portfolio data - in a live application, our tool would have queried for this information from the PMS.
* We are using `yfinance` to fetch live closing prices of our indexes (BSE, NSE, SP500, NASDAQ etc.)

## Step 3: Write the six callbacks and the agent

Create `agents/lesson07a_callbacks/wealth_advisor/callbacks.py`:

```python
"""Lesson 7a: Callbacks in Practice.

All six callback functions for the wealth management advisory agent,
kept in their own file so agent.py stays focused on what the agent
IS (its model, instruction, and tools) rather than what it DOES at
each interception point. Import these into agent.py; don't call them
from anywhere else directly, since ADK is the one doing the calling.

CRITICAL: ADK calls every callback using keyword arguments that must
match your parameter names exactly. The enforced names are:
  before_agent_callback / after_agent_callback : callback_context
  before_model_callback                        : callback_context, llm_request
  after_model_callback                         : callback_context, llm_response
  before_tool_callback                         : tool, args, tool_context
  after_tool_callback                          : tool, args, tool_context, tool_response

Using any other name raises a TypeError at runtime, not at import time.
"""

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types


# ── Before Agent ──────────────────────────────────────────────────────────────
# Mandatory parameter name: callback_context
# Fires: once per turn, before anything else.
# Returns Content to short-circuit the turn; returns None to proceed.

async def check_customer_tier(callback_context: CallbackContext):
    """Blocks access for unrecognised account tiers and tracks turn count.

    This is the right place for access control: no model tokens are
    spent if the request is going to be blocked anyway, and session
    bookkeeping here applies regardless of what the customer said.
    """
    valid_tiers = {"Standard", "Gold", "Platinum"}
    tier = callback_context.state.get("account_tier", "")

    if tier not in valid_tiers:
        return types.Content(
            role="model",
            parts=[types.Part(
                text=(
                    "Sorry, I'm unable to verify your account tier. "
                    "Please contact your branch for assistance."
                )
            )],
        )

    callback_context.state["turn_count"] = (
        callback_context.state.get("turn_count", 0) + 1
    )
    return None


# ── Before Model ──────────────────────────────────────────────────────────────
# Mandatory parameter names: callback_context, llm_request
# Fires: once per model call. In a turn with tools, fires MULTIPLE TIMES:
#   once before the model requests tools, and again before it generates
#   its final answer with tool results in context.
# Returns LlmResponse to skip the model call; returns None to proceed.

async def inject_market_context(callback_context: CallbackContext, llm_request):
    """Injects current market status into the system prompt dynamically.

    Only injects on the first model call per turn (before any tools have
    run). On the second call (after tool results are in context), skips
    the injection to avoid duplicating the market note.

    Note: the system instruction lives at llm_request.config.system_instruction,
    not directly on llm_request. We use the built-in append_instructions()
    method to add context cleanly rather than mutating parts directly.
    """
    has_tool_results = any(
        hasattr(msg, "parts")
        and any(
            hasattr(p, "function_response") and p.function_response
            for p in (msg.parts or [])
        )
        for msg in (llm_request.contents or [])
    )

    if not has_tool_results:
        market_note = (
            "Current market snapshot: BSE Sensex: 74,823 | "
            "Nifty50: 22,651 | S&P 500: 5,213. Markets are open."
        )
        llm_request.append_instructions([market_note])

    return None


# ── After Model ───────────────────────────────────────────────────────────────
# Mandatory parameter names: callback_context, llm_response
# Fires: once per model call (same multi-fire behaviour as before_model).
# Returns LlmResponse to replace the model's response; returns None to keep it.

async def scan_for_unsupported_advice(
    callback_context: CallbackContext, llm_response
):
    """Scans model output for specific investment advice language.

    This agent can discuss portfolios and market data but cannot give
    specific buy or sell recommendations. If the model output contains
    such language, replaces the response with a compliant one.
    """
    prohibited_phrases = [
        "i recommend buying",
        "you should sell",
        "i suggest purchasing",
    ]

    if not llm_response.content or not llm_response.content.parts:
        return None

    response_text = " ".join(
        p.text.lower() for p in llm_response.content.parts if p.text
    )

    if any(phrase in response_text for phrase in prohibited_phrases):
        from google.adk.models.llm_response import LlmResponse
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(
                    text=(
                        "I can share factual information about your portfolio "
                        "and current market conditions, but I'm not able to make "
                        "specific buy or sell recommendations. Please speak with "
                        "your relationship manager for personalised advice."
                    )
                )],
            )
        )

    return None


# ── Before Tool ───────────────────────────────────────────────────────────────
# Mandatory parameter names: tool, args, tool_context
# (NOT "tool_args" — the parameter is exactly "args")
# Fires: once per tool call. Can fire multiple times in one turn.
# Returns a dict to skip the tool; returns None to let it run.

async def log_tool_invocation(tool, args: dict, tool_context: ToolContext):
    """Logs every tool call to the session audit trail.

    Records tool name and arguments before the tool runs, so the log
    is accurate even if the tool later fails or its result is replaced
    by after_tool_callback.
    """
    audit_log = tool_context.state.get("audit_log", [])
    audit_log.append({"tool": tool.name, "args": args})
    tool_context.state["audit_log"] = audit_log
    return None


# ── After Tool ────────────────────────────────────────────────────────────────
# Mandatory parameter names: tool, args, tool_context, tool_response
# Fires: once per tool call.
# Returns a dict to replace the tool's result; returns None to keep it.

async def validate_tool_result(
    tool, args: dict, tool_context: ToolContext, tool_response: dict
):
    """Validates tool results before the model sees them.

    Catches obviously invalid data and replaces it with a structured
    error the model can handle gracefully.
    """
    if tool.name == "get_portfolio_summary":
        total = tool_response.get("total_value", 0)
        if isinstance(total, (int, float)) and total <= 0:
            return {
                "found": False,
                "error": (
                    "Portfolio data returned an invalid value. "
                    "Please try again or contact support."
                ),
            }
    return None


# ── After Agent ───────────────────────────────────────────────────────────────
# Mandatory parameter name: callback_context
# Fires: once per turn, after the agent's final response is ready.
# Returns Content to replace the final response; returns None to keep it.

async def save_to_memory(callback_context: CallbackContext):
    """Saves this turn to long-term memory for future session recall.

    Requires a memory_service to be wired into the Runner in main.py.
    Without one, this raises a ValueError at runtime.
    """
    await callback_context.add_session_to_memory()
    return None
    
```


Create `agents/lesson07a_callbacks/wealth_advisor/agent.py`:

```python
"""Lesson 7a: Callbacks in Practice.

Agent definition for the wealth management advisory agent. This file
declares what the agent IS: its model, instruction, tools, and which
callback functions are registered at each interception point. The
callback implementations live in callbacks.py.
"""

from google.adk.agents import Agent

from common.model_config import get_model
from .tools import get_portfolio_summary, get_market_indices
from .callbacks import (
    check_customer_tier,
    inject_market_context,
    scan_for_unsupported_advice,
    log_tool_invocation,
    validate_tool_result,
    save_to_memory,
)

AGENT_INSTRUCTION = (
    "You are a wealth management advisor for a private bank. You are "
    "speaking with {customer_name}, a {account_tier} tier customer. "
    "You can look up their portfolio summary and current market index "
    "levels. You can discuss their portfolio allocation, explain market "
    "movements, and answer general investment questions. You cannot make "
    "specific buy or sell recommendations; for those, direct the customer "
    "to their relationship manager. This is turn {turn_count?} of the "
    "current conversation."
)

root_agent = Agent(
    name="wealth_advisor_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description=(
        "Wealth management advisory agent with compliance guardrails, "
        "audit logging, and long-term memory across sessions."
    ),
    tools=[get_portfolio_summary, get_market_indices],
    before_agent_callback=check_customer_tier,
    before_model_callback=inject_market_context,
    after_model_callback=scan_for_unsupported_advice,
    before_tool_callback=log_tool_invocation,
    after_tool_callback=validate_tool_result,
    after_agent_callback=save_to_memory,
)
```

Create `agents/lesson07a_callbacks/wealth_advisor/__init__.py`:

```python
from . import agent
```

Let's step back and read through what the full callback chain does on a single typical turn: the customer asks about their portfolio. `check_customer_tier` runs first, confirms this is a valid tier, increments the turn counter, and lets the turn proceed. `inject_market_context` fires before the model call and appends the live market snapshot to the system prompt. The model decides it needs to call `get_portfolio_summary`. `log_tool_invocation` fires, records the call in the audit log before anything runs. The tool runs. `validate_tool_result` fires, checks the returned portfolio value is sensible. The model now calls itself again with the portfolio data included, `inject_market_context` fires again (but this time detects tool results are already present and skips the injection). The model produces its final answer. `scan_for_unsupported_advice` fires, finds no prohibited phrases, passes through. Finally `save_to_memory` fires, persisting the whole turn to long-term storage. Six callbacks, four of them firing at least once, two of them firing twice, all in service of one coherent answer to one customer question.

> 🎗️ **PARAMETER NAMING REMINDER:** Every callback is called by ADK using keyword arguments. Notice `log_tool_invocation`'s second parameter is named `args`, not `tool_args`. This is the exact name the source code uses when calling it, `args=function_args`. If you renamed it `tool_args` to match the variable name inside ADK's own code, you'd get a `TypeError` the first time any tool fired. The same applies to every other callback: `callback_context`, `llm_request`, `llm_response`, `tool_response`, all fixed, all enforced at runtime.

## Step 4: Write main.py

Create `agents/lesson07a_callbacks/main.py`:

```python
"""Lesson 7a: Callbacks in Practice.

Drives the wealth management advisory agent with a pre-seeded session
(simulating a CRM handoff, as in Lesson 6a) so the agent immediately
knows the customer's name and tier. The memory service is wired in so
after_agent_callback's call to add_session_to_memory() actually has
somewhere to persist data.

Run with:
    uv run agents/lesson07a_callbacks/main.py
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.genai import types

from wealth_advisor.agent import root_agent

APP_NAME = "wealth_advisor_app"
USER_ID = "demo_user"


async def main() -> None:
    """Runs a console wealth advisory conversation with all six callbacks active."""
    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()

    # Pre-seed CRM context exactly as Lesson 6a did, so the agent
    # knows who it's talking to before the first message.
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={
            "customer_name": "Arjun Mehta",
            "account_tier": "Platinum",
            "customer_id": "CUST001",
        },
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
        memory_service=memory_service,  # Required for after_agent_callback's
    )                                   # add_session_to_memory() to work.

    print("Wealth Management Advisor (type 'exit' to quit)\n")
    print(f"Customer: {session.state['customer_name']} "
          f"({session.state['account_tier']})\n")

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

        # Show live session state so you can watch callbacks mutating it.
        updated = await session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session.id
        )
        print(f"[state] turn_count={updated.state.get('turn_count')} | "
              f"audit_log entries={len(updated.state.get('audit_log', []))}\n")


if __name__ == "__main__":
    asyncio.run(main())
```

Notice `memory_service=InMemoryMemoryService()` is passed to the `Runner` here. In every earlier lesson, `main.py` created a `Runner` without a memory service, because no lesson until now needed one. The `after_agent_callback` calls `callback_context.add_session_to_memory()`, and ADK will raise a `ValueError` if that call is made but no memory service is configured on the runner. Wiring one in at the runner level is what makes `after_agent_callback`'s memory persistence actually work.

## Step 5: Run it

From the root folder run the following command.

```bash
uv run agents/lesson07a_callbacks/main.py
```

You should see the customer's name and tier printed, then a prompt. Try a question that will trigger both tools:

```
Can you give me an overview of my portfolio and how the markets are doing today?
```

Watch the `[state]` line that prints after each turn: `audit_log entries` should show 2 entries (one for each tool called), and `turn_count` should be 1.

Now try something that would normally produce investment advice:

```
Based on the market levels, should I be buying more equity right now?
```

The model might try to give a specific recommendation. If the `after_model_callback` catches a prohibited phrase, you'll see the compliant replacement response instead of whatever the model actually generated.

To test the access control, try editing `main.py` temporarily to change `"account_tier": "Platinum"` to `"account_tier": "Unknown"` and run again. The very first turn should return the block message without the model ever being called.

> **NOTE:** To test this agent with `adk run` or `adk web` for quick iteration, point them at the agent's subfolder: `adk run agents/lesson07a_callbacks/wealth_advisor` or `adk web agents/lesson07a_callbacks`. Note that `adk web` won't wire up the `InMemoryMemoryService`, so the `after_agent_callback`'s call to `add_session_to_memory()` will raise a `ValueError`. For testing all six callbacks properly, use `uv run agents/lesson07a_callbacks/main.py`.

## If you're coming from LangChain or LangGraph

LangGraph has a similar concept in its checkpointing and state management hooks, though they map slightly differently. LangGraph's `@chain.on_start`, `@chain.on_end`, and related event hooks give you observability points, but generally don't let you mutate or short-circuit the underlying operation the way ADK's callbacks do. ADK's approach is closer to middleware in a web framework: each callback is a genuine interception point where you can modify the data flowing through or stop it entirely. If you've used LangChain's `BaseCallbackHandler` for logging, ADK's `before_tool_callback` / `after_tool_callback` pair does the same job but with the added power of being able to actually change the tool's arguments or result before the rest of the system sees them.

## In this lesson

We wired all six ADK callbacks onto a single wealth management advisory agent, each doing a distinct, production-realistic job: access control before the turn runs, live market context injected before the model call, compliance scanning on model output, tool-call audit logging before tools execute, result validation after tools return, and long-term memory persistence after the turn closes. We also saw directly that `before_model_callback` and `after_model_callback` fire more than once in turns involving tools, and why `after_agent_callback` needs a `memory_service` wired into the `Runner` to actually do its job.

## In the next lesson

With callbacks fully in hand, we move to the other half of the memory picture: what happens when a session ends. Session state disappears with it, which is fine for a single advisory conversation, but not for a relationship manager assistant that needs to remember a client's preferences across entirely separate conversations days apart. The next lesson introduces ADK's memory service properly, using the `add_session_to_memory` pattern you've already seen in `save_to_memory` above, and shows how to search that memory from a brand new session.
