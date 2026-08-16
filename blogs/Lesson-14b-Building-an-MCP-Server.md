# Lesson 14b: Building Your Own MCP Server

In the previous lesson `14a` we connected to a server someone else built and maintains, Stripe's. In this lesson we build one of our own, a mutual fund data server using the standalone `mcp` SDK. Then it gets consumed back, over both transports, `stdio` and streamable HTTP.

## What we're building

This lesson builds a server that answers one simple question about any mutual fund, no matter where it's from: _what's it worth right now_, and _how has it moved recently_? An agent can ask about _any_ mutual fund, be it from India or from anywhere else, without needing to know anything about where the underlying data actually comes from. That's the server's job to figure out, not the agent's.

The real challenge for this specific implementation is that mutual funds split into two genuinely different worlds:

* Indian mutual funds are identified by a numeric AMFI scheme code, and their data comes from `api.mfapi.in`, an unauthenticated wrapper around AMFI's own daily NAV feed. It's free, you don't need any API key nor any signups 😊.
* Conversely, global mutual funds, including US MFs, are identified by a ticker symbol, such as `VFIAX`. We'll be using `yfinance` to fetch non-India MF data. `yfinance` cannot be used for India MFs as it relies on data from MorningStar.

We'll be implementing 5 tools to make this happen:

* `search_indian_mf_schemes`, `get_indian_mf_nav`, and `get_indian_mf_nav_history` for the Indian side.
* `get_global_mf_price` and `get_global_mf_price_history` for the global side.

All 5 tools sit on the same MCP server. The calling agent's model decides which one applies, based on whether it's looking at a numeric scheme code or a ticker symbol, exactly the same kind of judgment call Lesson `11d`'s routing example made between two specialist agents.

> **NOTE:** Both `api.mfapi.in` and `yfinance` are real, live, external services. The data this server returns depends on your own environment having ordinary internet access, and on both services being reachable at the time you run it.

## Step 1: Install what this lesson needs

Three new packages, all before writing a line of code, so nothing in the steps below hits an unresolved import:

```bash
uv add "google-adk[mcp]==2.5.0" httpx yfinance
```

`google-adk[mcp]` pulls in the full `mcp` SDK AND `mcp.server.fastmcp.FastMCP`, which is the class this lesson's server is built on. You don't need a separate install of the `mcp` package. 

`httpx` is an HTTP client required for Indian mutual fund data. 

`yfinance` was already installed in previous lessons. It's _strictly_ not a new package to install. We added this to the installs list in case you jumped straight to this lesson. Even if you did install it previously, adding it again won't do much much harm. `uv` will just confirm that it's alredy there!

## Step 2: Set up the folder structure

```
agents/lesson14b_mcp_server/
├── main.py
├── nav_server/
│   ├── __init__.py
│   ├── indian_mf.py
│   ├── global_mf.py
│   └── server.py
└── nav_consumer/
    ├── __init__.py
    └── agent.py
```

`nav_server/` is the server, built with the `mcp` SDK directly, nothing ADK-specific in it. `nav_consumer/` is the ADK side, agents that connect to it with `McpToolset`.

## Step 3: Build the Indian mutual fund data module

Create `agents/lesson14b_mcp_server/nav_server/indian_mf.py`

```python
"""Lesson 14b: Real Indian mutual fund data via api.mfapi.in.

api.mfapi.in is a free, unauthenticated wrapper around AMFI's own daily
NAV feed. No API key, no signup needed!
"""

from datetime import datetime

import httpx

BASE_URL = "https://api.mfapi.in/mf"


async def search_indian_mf_schemes(query: str) -> list[dict]:
    """Searches Indian mutual fund schemes by name.

    Args:
        query: Text to search for, e.g. "HDFC Flexi Cap" or "SBI Bluechip".

    Returns:
        A list of matching schemes, each with scheme_code and
        scheme_name, capped at 10 results.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{BASE_URL}/search", params={"q": query})
        response.raise_for_status()
        results = response.json()

    return [
        {"scheme_code": str(r["schemeCode"]), "scheme_name": r["schemeName"]}
        for r in results[:10]
    ]


async def get_indian_mf_nav(scheme_code: str) -> dict:
    """Fetches the latest NAV for an Indian mutual fund scheme.

    Args:
        scheme_code: The AMFI scheme code, e.g. "119551". Use
            search_indian_mf_schemes first if you only have a fund name.

    Returns:
        A dict with scheme_code, scheme_name, nav, date, and currency
        ("INR"), or an error field if the scheme code isn't found.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{BASE_URL}/{scheme_code}/latest")

    if response.status_code != 200:
        return {"error": f"Could not find scheme_code: {scheme_code}"}

    data = response.json()
    entries = data.get("data", [])
    if not entries:
        return {"error": f"No NAV data available for scheme_code: {scheme_code}"}

    meta = data.get("meta", {})
    latest = entries[0]
    return {
        "scheme_code": scheme_code,
        "scheme_name": meta.get("scheme_name", ""),
        "nav": float(latest["nav"]),
        "date": latest["date"],
        "currency": "INR",
    }


async def get_indian_mf_nav_history(scheme_code: str, days: int) -> dict:
    """Fetches recent NAV history for an Indian mutual fund scheme.

    Args:
        scheme_code: The AMFI scheme code, e.g. "119551".
        days: How many most recent days of history to return.

    Returns:
        A dict with scheme_code, scheme_name, currency, and history, a
        list of {date, nav} entries, most recent first. Error field if
        the scheme code isn't found.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{BASE_URL}/{scheme_code}")

    if response.status_code != 200:
        return {"error": f"Could not find scheme_code: {scheme_code}"}

    data = response.json()
    entries = data.get("data", [])
    if not entries:
        return {"error": f"No NAV data available for scheme_code: {scheme_code}"}

    # api.mfapi.in returns the entire history; sort explicitly rather than
    # assume its ordering, then take the most recent `days` entries.
    parsed = [
        {"date_obj": datetime.strptime(e["date"], "%d-%m-%Y"), "date": e["date"], "nav": float(e["nav"])}
        for e in entries
    ]
    parsed.sort(key=lambda e: e["date_obj"], reverse=True)
    recent = parsed[:days]

    meta = data.get("meta", {})
    return {
        "scheme_code": scheme_code,
        "scheme_name": meta.get("scheme_name", ""),
        "currency": "INR",
        "history": [{"date": e["date"], "nav": e["nav"]} for e in recent],
    }
```

`api.mfapi.in`'s history endpoint returns a fund's *entire* NAV history in one response, no date-range parameter. The sort-then-slice here isn't extra caution for its own sake, the API's own ordering isn't documented, so sorting explicitly by parsed date, rather than trusting whatever order the response happens to arrive in, is what actually makes `days` mean what it says.

## Step 4: Build the global mutual fund data module

```python
# agents/lesson14b_mcp_server/nav_server/global_mf.py
"""Lesson 14b: Real global mutual fund data via yfinance.

Covers non-Indian funds, identified by ticker rather than an AMFI
scheme code, e.g. VFIAX for Vanguard 500 Index Fund Admiral Shares.
yfinance itself is synchronous, so calls run in a thread via
asyncio.to_thread, keeping this an async tool without blocking the
server's event loop.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import asyncio

import yfinance as yf


def _fetch_latest_price(ticker: str) -> dict | None:
    history = yf.Ticker(ticker).history(period="5d")
    if history.empty:
        return None
    last_row = history.iloc[-1]
    return {
        "ticker": ticker.upper(),
        "price": round(float(last_row["Close"]), 4),
        "date": history.index[-1].strftime("%Y-%m-%d"),
        "currency": "USD",
    }


def _fetch_price_history(ticker: str, days: int) -> dict | None:
    history = yf.Ticker(ticker).history(period=f"{max(days, 5)}d")
    if history.empty:
        return None
    recent = history.tail(days)
    entries = [
        {"date": idx.strftime("%Y-%m-%d"), "price": round(float(row["Close"]), 4)}
        for idx, row in recent.iterrows()
    ]
    return {"ticker": ticker.upper(), "currency": "USD", "history": list(reversed(entries))}


async def get_global_mf_price(ticker: str) -> dict:
    """Fetches the latest price for a global (e.g. US) mutual fund.

    Args:
        ticker: The fund's ticker symbol, e.g. "VFIAX". Not for Indian
            mutual funds, use get_indian_mf_nav for those.

    Returns:
        A dict with ticker, price, date, and currency ("USD"), or an
        error field if the ticker isn't found.
    """
    result = await asyncio.to_thread(_fetch_latest_price, ticker)
    if result is None:
        return {"error": f"Could not find ticker: {ticker}"}
    return result


async def get_global_mf_price_history(ticker: str, days: int) -> dict:
    """Fetches recent price history for a global (e.g. US) mutual fund.

    Args:
        ticker: The fund's ticker symbol, e.g. "VFIAX".
        days: How many most recent days of history to return.

    Returns:
        A dict with ticker, currency, and history, a list of
        {date, price} entries, most recent first. Error field if the
        ticker isn't found.
    """
    result = await asyncio.to_thread(_fetch_price_history, ticker, days)
    if result is None:
        return {"error": f"Could not find ticker: {ticker}"}
    return result
```

Notice both `get_indian_mf_nav` and `get_global_mf_price` return the same shape of dict, `date`/`nav` or `date`/`price` plus an explicit `currency` field, INR on one side, USD on the other. That's deliberate: the calling agent shouldn't need to know or care which backend actually answered, only that whatever it got back is clearly labeled.

## Step 5: Build the server

```python
# agents/lesson14b_mcp_server/nav_server/server.py
"""Lesson 14b: Mutual fund data MCP server, runnable over stdio or streamable HTTP.

Two families of tools, Indian mutual funds (via api.mfapi.in) and
global mutual funds (via yfinance), both real data, no mocks.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import argparse

from mcp.server.fastmcp import FastMCP

from nav_server.global_mf import get_global_mf_price, get_global_mf_price_history
from nav_server.indian_mf import (
    get_indian_mf_nav,
    get_indian_mf_nav_history,
    search_indian_mf_schemes,
)

mcp = FastMCP("mutual-fund-data")

mcp.tool()(search_indian_mf_schemes)
mcp.tool()(get_indian_mf_nav)
mcp.tool()(get_indian_mf_nav_history)
mcp.tool()(get_global_mf_price)
mcp.tool()(get_global_mf_price_history)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mutual fund data MCP server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio for a local subprocess, http for a small hosted service.",
    )
    parser.add_argument("--port", type=int, default=8090, help="Port for --transport http.")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.settings.port = args.port
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
```

`mcp.tool()(some_function)` registers an already-defined function as a tool, the same thing `@mcp.tool()` does when it sits directly above a function definition, just usable here since these five functions are imported from two other modules rather than defined in this file.

## Step 6: Build the consuming agents

```python
# agents/lesson14b_mcp_server/nav_consumer/agent.py
"""Lesson 14b: Agent factory functions, one per transport, same MCP server.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import sys
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import (
    McpToolset,
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters

from common.model_config import get_model

instruction = """You are a mutual fund research assistant, covering both
Indian and global funds.

Indian mutual funds are identified by a numeric AMFI scheme code, e.g.
119551. If you only have a fund name, call search_indian_mf_schemes
first, then get_indian_mf_nav or get_indian_mf_nav_history.

Global (e.g. US) mutual funds are identified by a ticker symbol, e.g.
VFIAX. Use get_global_mf_price or get_global_mf_price_history for
these, never for Indian funds, the identifiers aren't interchangeable.

Always call the appropriate tool, never estimate a NAV or price
yourself.
"""


def make_stdio_nav_agent(nav_server_dir: str) -> Agent:
    """Builds an agent that spawns the MCP server itself, over stdio.

    No separate process needed, McpToolset launches
    `python -m nav_server.server --transport stdio` as a subprocess and
    talks to it directly.

    Args:
        nav_server_dir: The working directory to launch the server
            subprocess from, so its own `nav_server` package resolves.

    Returns:
        An Agent connected to the MCP server over stdio.
    """
    return Agent(
        name="mf_research_agent_stdio",
        model=get_model("primary"),
        description="Looks up Indian and global mutual fund data via a locally spawned MCP server, over stdio.",
        instruction=instruction,
        tools=[
            McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command=sys.executable,
                        args=["-m", "nav_server.server", "--transport", "stdio"],
                        cwd=nav_server_dir,
                    ),
                    timeout=15,
                ),
            ),
        ],
    )


def make_http_nav_agent(port: int = 8090) -> Agent:
    """Builds an agent that connects to an already-running MCP server, over HTTP.

    Unlike the stdio version, this doesn't start the server itself, it
    has to already be running, in a separate terminal, with:
        uv run python -m nav_server.server --transport http --port 8090

    Args:
        port: The port the MCP server's HTTP transport is listening on.

    Returns:
        An Agent connected to the MCP server over streamable HTTP.
    """
    return Agent(
        name="mf_research_agent_http",
        model=get_model("primary"),
        description="Looks up Indian and global mutual fund data via a remote MCP server, over streamable HTTP.",
        instruction=instruction,
        tools=[
            McpToolset(
                connection_params=StreamableHTTPConnectionParams(
                    url=f"http://127.0.0.1:{port}/mcp",
                ),
            ),
        ],
    )


# adk web / adk run look for a variable named root_agent. The stdio
# version is the one that works standalone, no separate server process
# needed first.
root_agent = make_stdio_nav_agent(nav_server_dir=str(Path(__file__).resolve().parent.parent))
```

The instruction is the only thing actually teaching the model to route correctly, numeric code versus ticker symbol. Nothing in the tool wiring itself enforces that distinction, it's the model reading the two identifier formats and picking the matching tool, the same judgment call, applied to two tool families instead of two whole agents.

## Step 7: Wire up main.py

```python
# agents/lesson14b_mcp_server/main.py
"""Lesson 14b: Run the mutual fund consumer agent against the server we built.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))  # adds agents/ for common.*
sys.path.insert(0, str(THIS_DIR))  # adds this lesson's own folder for nav_server/nav_consumer

from google.adk.sessions import InMemorySessionService

from common.runner_utils import run_agent_query
from nav_consumer.agent import make_http_nav_agent, make_stdio_nav_agent

APP_NAME = "lesson14b_mcp_server"
USER_ID = "console_user"

QUERIES = [
    "What's the current NAV for AMFI scheme code 119551, and how has it moved over the last 5 days?",
    "What's the current price for the Vanguard 500 Index Fund Admiral Shares, ticker VFIAX?",
]


async def run_stdio_demo() -> None:
    """Runs both queries against the stdio-connected agent, which spawns the server itself."""
    print("=== Transport 1: stdio (server spawned automatically) ===\n")

    agent = make_stdio_nav_agent(nav_server_dir=str(THIS_DIR))
    session_service = InMemorySessionService()
    for query in QUERIES:
        print("Query:", query)
        response = await run_agent_query(
            agent=agent,
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=str(uuid.uuid4()),
            query=query,
            session_service=session_service,
        )
        print("Response:", response)
        print()


async def run_http_demo(port: int) -> None:
    """Runs both queries against the HTTP-connected agent, which expects the server already running."""
    print("=== Transport 2: streamable HTTP (server must already be running) ===")
    print(f"Expecting: uv run python -m nav_server.server --transport http --port {port}\n")

    agent = make_http_nav_agent(port=port)
    session_service = InMemorySessionService()
    try:
        for query in QUERIES:
            print("Query:", query)
            response = await run_agent_query(
                agent=agent,
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=str(uuid.uuid4()),
                query=query,
                session_service=session_service,
            )
            print("Response:", response)
            print()
    except Exception as exc:
        print(f"Could not reach the HTTP server on port {port}: {exc}")
        print("Start it first, in a separate terminal, then rerun with --transport http.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Lesson 14b mutual fund consumer demo.")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()

    if args.transport == "stdio":
        await run_stdio_demo()
    else:
        await run_http_demo(port=args.port)


if __name__ == "__main__":
    asyncio.run(main())
```

Two queries this time, not one, one Indian scheme by code, one global fund by ticker, run back to back through the same agent. Watching which tool gets called for each is the actual point, the agent should reach for `get_indian_mf_nav` on the first and `get_global_mf_price` on the second, without being told explicitly which is which beyond what the instruction already set up.

## Step 8: Run it

The stdio version, self-contained, one command:

```bash
uv run agents/lesson14b_mcp_server/main.py
```

You should see the agent correctly pick `get_indian_mf_nav` and `get_indian_mf_nav_history` for the first query, and `get_global_mf_price` for the second, coming back with real, current figures for both, an actual NAV in INR, an actual price in USD.

The HTTP version needs two terminals. In the first, start the server:

```bash
uv run python -m nav_server.server --transport http --port 8090
```

(run this from inside `agents/lesson14b_mcp_server/`, so `nav_server` resolves as a package). In the second terminal:

```bash
uv run agents/lesson14b_mcp_server/main.py --transport http
```

Same two queries, same tool selection, this time reaching the server over an actual HTTP connection instead of a spawned subprocess. Stop the server in the first terminal with Ctrl+C when you're done.

## Try it in adk web too

```bash
adk web agents
```

Select `lesson14b_mcp_server.nav_consumer`. This loads the stdio version, `adk web` spawns the server itself the same way `main.py` does, nothing extra to start first.

## If you're coming from LangChain or LangGraph

Building an MCP server is entirely outside either framework's own scope, they're consumers, not server-building tools, same as ADK. The `mcp` SDK you used here, specifically `FastMCP`, is the standard way to build a server regardless of which framework ends up consuming it, a LangChain agent could connect to this exact same server with no changes to `nav_server/` at all, only the consuming code would differ.

## In this lesson

You built a real MCP server from scratch, five tools across two genuinely different data sources, `api.mfapi.in` for Indian mutual funds, `yfinance` for global ones, using the standalone `mcp` SDK's `FastMCP`, nothing ADK-specific in the server itself. You ran it two genuinely different ways from the same code, `stdio`, spawned automatically, and streamable HTTP, running as its own process. On the consuming side, one agent, one instruction, correctly routed two different queries to two different tool families based on nothing but the shape of the identifier each query used, numeric scheme code versus ticker symbol, the same kind of judgment call Lesson 11d's routing example made between whole agents, here made between tool families on a single server.

## In the next lesson

The next lesson covers Agent-to-Agent delegation, cross-service A2A between two separate processes, building on the `AgentTool` foundation from Lesson 11d.
