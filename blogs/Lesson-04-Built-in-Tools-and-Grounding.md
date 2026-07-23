# Lesson 4: Built-in Tools & Grounding

Lesson 3 gave an agent function tools you wrote yourself. This lesson introduces a different category: tools that ADK ships built in, where the model calls out to a capability Google runs on its own infrastructure rather than code sitting in your project. We'll build both kinds side by side, and along the way you'll hit a real, current limitation: ADK's flagship built-in tool, Google Search grounding, only works with Gemini models. Since Claude is our default for this series, we're going to build a genuine, working alternative rather than skip the topic.

## The problem we're solving

A wealth management desk's investment research team gets asked two kinds of questions constantly: "What's Reliance Industries trading at right now?" and "Why did Tesla's stock move today?" The first is a data lookup, exactly the kind of thing Lesson 3's function tools handle well. The second is different: it needs current information from the open web, something that changed today, which no model's training data can possibly contain.

That second kind of question is what "grounding" means in this context: giving a model access to live, current information from outside its training data, so its answer reflects what's actually happening right now rather than what was true whenever it was trained. We're going to build a market briefing agent that handles both: live prices via a function tool (which you already know how to do from Lesson 3), and current news via grounding (which is new).

## Built-in tools versus function tools

A function tool, like the ones from Lesson 3, is code you write and ADK exposes to the model. A built-in tool is different: it's a capability the model provider runs internally, on their own servers, as part of generating a response. When you give Gemini the `google_search` built-in tool, Gemini itself performs the search as part of its inference process and folds the results into its answer, you never see a separate "search API call" happening in your code the way you would with a function tool.

This distinction matters because of how it's implemented. Built-in tools are wired into a specific model provider's infrastructure, they're not portable code you can hand to any model. That's the whole reason `google_search` is Gemini-only: it depends on machinery inside Google's model-serving stack that simply doesn't exist for Claude. Function tools have no such restriction, since they're just Python functions ADK calls on your behalf, which is exactly why our Claude-side solution in this lesson is a function tool that does the equivalent job.

## Step 1: Add shared finance tools

We're extending the `agents/common/` package from Lesson 3 with tools any BFSI agent in this series might reuse: live stock prices and stock news search.

Add two dependencies:

```bash
uv add yfinance ddgs
```

`yfinance` pulls market data from Yahoo Finance for free, no API key required, and works for US, Indian (NSE/BSE), and European tickers alike. `ddgs` is a free, no-API-key wrapper around DuckDuckGo's search, and it's the piece doing double duty in this lesson: a normal function tool for fetching news, and, not incidentally, our working substitute for `google_search` when running on Claude.

Create `agents/common/finance_tools.py`:

```python
"""Shared market-data and news tools for BFSI investment research agents."""

import yfinance as yf
from ddgs import DDGS


def get_stock_price(ticker: str) -> dict:
    """Fetches the latest closing price and day-over-day change for a stock.

    Args:
        ticker: The stock ticker symbol, using Yahoo Finance conventions.
            Examples: "AAPL" for Apple (US), "RELIANCE.NS" for Reliance
            Industries (India, NSE), "SAP.DE" for SAP (Germany, Xetra).

    Returns:
        A dict with the latest close price, previous close, percent
        change, currency, and the company name, or an error message
        if the ticker could not be found.
    """
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period="5d")

        if history.empty:
            return {
                "found": False,
                "ticker": ticker,
                "error": (
                    "No price data found for this ticker. Check the "
                    "symbol and, for non-US exchanges, the suffix "
                    "(e.g. .NS for India, .DE for Germany)."
                ),
            }

        latest = history.iloc[-1]
        previous = history.iloc[-2] if len(history) > 1 else latest
        latest_close = float(latest["Close"])
        previous_close = float(previous["Close"])
        change_percent = (
            ((latest_close - previous_close) / previous_close) * 100
            if previous_close
            else 0.0
        )

        company_name = ticker
        currency = ""
        try:
            info = stock.info
            company_name = info.get("longName") or info.get("shortName") or ticker
            currency = info.get("currency", "")
        except Exception:
            pass

        return {
            "found": True,
            "ticker": ticker,
            "company_name": company_name,
            "latest_close": round(latest_close, 2),
            "previous_close": round(previous_close, 2),
            "change_percent": round(change_percent, 2),
            "currency": currency,
            "as_of_date": str(latest.name.date()),
        }
    except Exception as error:
        return {"found": False, "ticker": ticker, "error": str(error)}


def get_stock_news(company_or_ticker: str, max_results: int = 5) -> dict:
    """Searches the web for recent news about a company or stock.

    This is a free, provider-agnostic alternative to ADK's built-in
    google_search tool. It works with any model, including Claude,
    since it's a plain function tool rather than a model built-in.

    Args:
        company_or_ticker: The company name or ticker symbol to search
            news for, e.g. "Tata Motors" or "TSLA".
        max_results: Maximum number of news results to return.
            Defaults to 5.

    Returns:
        A dict with a list of articles, each containing a title,
        short snippet, and source URL.
    """
    try:
        query = f"{company_or_ticker} stock news"
        results = DDGS().text(query, max_results=max_results)
        articles = [
            {
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
            }
            for r in results
        ]
        return {"found": bool(articles), "query": query, "articles": articles}
    except Exception as error:
        return {"found": False, "query": company_or_ticker, "error": str(error)}
```

Both functions return a dict with a `found` flag and either the data or an error message, rather than letting an exception escape. This matters for tool functions specifically: if `get_stock_price` raised an uncaught exception on a bad ticker, the whole agent turn would fail. Returning a structured "not found" result instead lets the model see what went wrong and respond sensibly, for example by asking the customer to double check the ticker symbol, which is a much better experience than the agent silently erroring out.

`get_stock_price` uses `stock.history()` rather than `stock.info` as the primary source for the price itself. Yahoo Finance's `.info` endpoint is known to be less reliable and more prone to rate-limiting than the historical-data endpoint, so we only fall back to `.info` for the company name, and we wrap that specific call in its own `try/except` so a failure there doesn't take down the whole function.

## Step 2: Build the Claude-side agent (our google_search alternative)

Create `agents/lesson04_market_briefing/agent.py`:

```python
"""BFSI Lesson 4: Built-in Tools & Grounding (Claude variant).

A market briefing agent for an investment research desk. Live prices
come from a function tool; current news comes from a second function
tool wrapping a free web search, standing in for ADK's built-in
google_search tool, which does not support Claude models.
"""

from google.adk.agents import Agent

from common.model_config import get_model
from common.finance_tools import get_stock_price, get_stock_news

AGENT_INSTRUCTION = (
    "You are an investment research assistant for a wealth management "
    "desk. Use get_stock_price when a customer asks about a stock's "
    "current or recent price. Use get_stock_news when a customer asks "
    "why a stock moved, or wants recent news about a company. Always "
    "cite that news came from a web search, and include source URLs "
    "when you report on news articles. If a ticker can't be found, "
    "ask the customer to confirm the symbol and exchange rather than "
    "guessing. You are not providing investment advice, only "
    "factual information; if asked for a recommendation, say so "
    "clearly and suggest they speak with a licensed advisor."
)

root_agent = Agent(
    name="market_briefing_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description=(
        "Provides live stock prices and recent news for investment "
        "research, using Claude with a web-search function tool."
    ),
    tools=[get_stock_price, get_stock_news],
)
```

Create `agents/lesson04_market_briefing/__init__.py`:

```python
from . import agent
```

There's nothing structurally new in this file if you've done Lesson 3: two function tools, imported from the shared `common` package this time instead of a lesson-local `tools.py`, since both are reusable across future lessons. The instruction is worth reading closely, though. It tells the model explicitly to cite sources and include URLs for news, and to decline giving investment advice. Neither of those behaviors happens automatically. A model asked "why did this stock move" will happily generate a plausible-sounding explanation without a source unless told to ground its answer in what the tool actually returned, and a model asked "should I buy this stock" will often just answer unless it's told that's out of scope. In a BFSI context, both of these are the kind of thing that turns into a compliance problem if left to the model's default behavior.

## Step 3: Build the Gemini-side agent (the real built-in tool)

This is the variant that actually uses ADK's built-in `google_search` tool, so you can see it working and compare it directly to the Claude version.

Create `agents/lesson04_market_briefing_gemini_grounded/agent.py`:

```python
"""BFSI Lesson 4: Built-in Tools & Grounding (Gemini variant).

The same market briefing agent, but using ADK's built-in google_search
tool for news grounding instead of a custom function tool. This only
works with Gemini models, which is the whole point of this variant:
seeing the real built-in tool alongside its Claude-compatible
alternative from Step 2.
"""

from google.adk.agents import Agent
from google.adk.tools.google_search_tool import GoogleSearchTool

from common.finance_tools import get_stock_price

AGENT_INSTRUCTION = (
    "You are an investment research assistant for a wealth management "
    "desk. Use get_stock_price when a customer asks about a stock's "
    "current or recent price. Use your built-in search grounding when "
    "a customer asks why a stock moved, or wants recent news. Always "
    "cite sources for anything drawn from search results. You are not "
    "providing investment advice, only factual information."
)

root_agent = Agent(
    name="market_briefing_agent_gemini_grounded",
    model="gemini-flash-latest",
    instruction=AGENT_INSTRUCTION,
    description=(
        "Provides live stock prices and Google-Search-grounded news, "
        "using Gemini's built-in search grounding tool."
    ),
    tools=[get_stock_price, GoogleSearchTool(bypass_multi_tools_limit=True)],
)
```

Create `agents/lesson04_market_briefing_gemini_grounded/__init__.py`:

```python
from . import agent
```

Two things in this file need explaining, and both are caveats you'll want to remember.

First: `google_search` is a singleton instance ADK exports directly (`from google.adk.tools import google_search`), and for a single-tool agent you'd normally just drop that straight into the `tools` list. Here, we're constructing `GoogleSearchTool(bypass_multi_tools_limit=True)` ourselves instead. That's because Gemini's built-in tools historically could not be combined with any other tool in the same agent, only one built-in tool, alone, per agent. Since we also want `get_stock_price` in this agent, we need the explicit workaround flag. Under the hood, setting it causes ADK to run the search as an isolated sub-agent call rather than a true inline model built-in, which is a reasonable trade-off: you get both tools working together, at the cost of an extra model call happening behind the scenes when search is actually used.

Second, and this is the core limitation of the lesson: if you swap `model="gemini-flash-latest"` for a Claude model in this specific file, it will fail. `GoogleSearchTool` checks the model name at request time and raises an error for anything that isn't Gemini. This isn't a bug or an oversight, it's a hard architectural limitation, since the search happens inside Gemini's own inference process, and Claude has no equivalent mechanism for ADK to hook into. That's exactly the gap Step 2's `get_stock_news` function tool exists to close.

## Step 4: Run both variants

From your project root, use `adk web` to see them side by side:

```bash
uv run adk web agents
```

Open the printed URL and you'll see both agents in the dropdown: `lesson04_market_briefing` (Claude) and `lesson04_market_briefing_gemini_grounded` (Gemini). Try the same two questions against each.

Ask about a price:

```
What's Reliance Industries trading at? Ticker is RELIANCE.NS
```

Both agents should call `get_stock_price` and come back with a current close price, the previous close, and the percentage move, worded as a short factual statement.

Then ask about news:

```
Why has Tesla's stock been moving this week?
```

On the Claude agent, you should see it call `get_stock_news`, then summarize what it found with source URLs attached. On the Gemini agent, you won't see an explicit tool call for search in the same way, since it's happening inside Gemini's own generation process, but the final answer should similarly reflect current news with cited sources. Compare the two answers: they're pulling from different search backends (DuckDuckGo versus Google's own grounding), so the specific articles referenced may differ, but both should be grounded in real, current information rather than a generic, dated summary.

If you're curious what happens when you push past the limitation, try editing the Gemini variant's `agent.py` to use `model="claude-haiku-4-5-20251001"` (wrapped in `AnthropicLlm`, as always) while keeping `GoogleSearchTool` in its tools list, then ask it a news question. You should see it fail with an error naming the model as unsupported for Google Search, exactly the restriction described above. Revert the change once you've seen it.

## If you're coming from LangChain or LangGraph

LangChain has an equivalent split, though it draws the line slightly differently. Provider-hosted capabilities, like OpenAI's hosted web search or code interpreter tools, work only with that provider's models, the same restriction we just hit with `google_search` and Gemini. Anything you'd build with a `Tool` or `@tool`-decorated function in LangChain, wrapping a search API, a database call, or any external service yourself, is portable across whatever model you point LangChain at, exactly like our `get_stock_news` function here. If you've previously reached for a search API wrapper in LangChain rather than a provider's built-in browsing tool for portability reasons, you already understand the trade-off this lesson is demonstrating.

## How this addressed the problem

The investment research desk started with two categories of question, one needing current data ADK can fetch as structured facts, one needing current information from the open web. We solved the first with an ordinary function tool, the same pattern from Lesson 3. We solved the second two ways: the "native" way, using Gemini's built-in search grounding, and a portable way, using a free function tool that gets Claude to the same outcome. Since Claude is this series' default, having a working, non-Gemini path to grounded, cited answers means the model policy from the series introduction holds up even for a capability ADK markets as Gemini-exclusive.

## A word on cost

Stock price lookups via `yfinance` are free and don't touch your LLM token budget at all, they're a direct data fetch, not a model call. `ddgs` search is also free, though it's worth knowing it's an unofficial wrapper around DuckDuckGo's public search, not a paid, rate-limited API with guarantees, so avoid hammering it with rapid repeated queries in a real application; for production BFSI use, you'd eventually want a licensed news or search API with an SLA. On the model side, each of these questions costs one or two Claude Haiku exchanges, still a fraction of a cent. The Gemini variant's grounded search, when `bypass_multi_tools_limit` triggers its sub-agent call, uses one extra Gemini call per search, still comfortably inside Gemini Flash's free tier for this kind of testing volume.

Ready for Lesson 5, where we make sure an agent's output isn't just words, using structured output to get a validated, guaranteed-shape response back from a credit risk scoring agent.
