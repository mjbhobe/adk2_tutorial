# Lesson 4: Built-in Tools

Lesson 3 gave an agent function tools you wrote yourself. This lesson introduces a different category: tools that ADK ships built in, where the model calls out to a capability Google runs on its own infrastructure rather than code sitting in your project. We'll build an agent with one directly - `google_search`, hit a real, current limitation along the way, and then build a genuine, working alternative for Claude, since Claude is our default for this series.

## The problem we're solving

A wealth management desk's investment research team gets asked two kinds of questions constantly: "What's Reliance Industries trading at right now?" and "Why did Tesla's stock move today?" The first is a data lookup, exactly the kind of thing Lesson 3's function tools handle well. The second request would need a slightly different approach - get the latest information from the web about Tesla to the LLM and let it figure out why Tesla's stock moved today, because it could very well be related to some _market event_. That's exactly what Google's search excels
at, and what we are going to leverage for the 2nd kind of request.

We're going to build a market briefing agent that handles both: live prices via a function tool, and current news via web search. For live stock prices we'll use the `yfinance` library and we'll use an internal tool `google_search` for web searching.

Add the dependency, by running the following commands on a terminal from the project root folder.

```bash
# ensure your uv environment is active
source .venv/bin/activate # or .venv\Scripts\activate on Windows
# add the yfinance module
uv add yfinance
```

`yfinance` pulls market data from Yahoo Finance for free, no API key required, and works for US, Indian (NSE/BSE), and European tickers alike. No additional dependencies required for `google_search` as it's a tool built into the ADK by Google.

Create the shared tools file. We're putting this in the `agents/common/` folder, since a stock price lookup is generic enough to be reused by other lessons later in this series.

Create `agents/common/finance_tools.py`:

```python
"""Shared market-data tools for BFSI investment research agents."""

import yfinance as yf


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
                    f"No price data found for this ticker ({ticker})." 
                    f"Check the symbol and, for non-US exchanges, the suffix "
                    f"(e.g. .NS for India, .DE for Germany)."
                ),
            }

        # grab last record in history
        latest = history.iloc[-1]
        # grab prev to last record in history, if it exists, else use last
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
```

This returns a dict with a `found` flag and either the data or an error message, rather than letting an exception escape. That matters specifically for tool functions: if this raised an uncaught exception on a bad ticker, the whole agent turn would fail. Returning a structured "not found" result instead lets the model see what went wrong and respond sensibly, for example by asking the customer to double check the ticker symbol.

> 📌**NOTE:** Every tool function in this series returns a dict, and it's worth knowing why, since it's not an arbitrary style choice. 
>
> The underlying **function-calling spec** that Gemini, Claude, and most providers share **requires a tool's result to reach the model as a dict-shaped payload**. ADK enforces this at the framework level: if a tool returns anything other than a `dict` shaped result, for example a plain string, a number, a list, then ADK will automatically wrap it into `{"result": <value>}` dict before sending it back, so returning a non-dict wouldn't actually break anything.
>
> Returning a dict yourself is what gives you control over that shape instead of accepting the generic, unlabeled `result` wrapper. It's also what makes error handling legible to ADK itself: `FunctionTool` includes a built-in telemetry hook that checks specifically for a dict containing an `error` key to detect and log tool failures. The `found` / `error` pattern used here isn't just readable to the model, it's a shape ADK's own internals are already built to recognize.

Notice too that `get_stock_price` uses `stock.history()` rather than `stock.info` as the primary source for the price itself. Yahoo Finance's `.info` endpoint is known to be less reliable and more prone to rate-limiting than the historical-data endpoint, so we only fall back to `.info` for the company name, wrapped in its own `try/except` so a failure there doesn't take down the whole function.

Now let's code the agent. Create `agents/lesson04_built_in_tools/agent.py`:

```python
"""Lesson 4: Built-in Tools 

A market briefing agent for an investment research desk, using
Gemini's built-in google_search tool for news grounding alongside a
function tool for live stock prices.
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
    "providing investment advice, only factual information; if asked "
    "for a recommendation, say so clearly and suggest they speak with "
    "a licensed advisor."
)

root_agent = Agent(
    name="market_briefing_agent",
    model= "gemini-3.5-flash-lite",
    instruction=AGENT_INSTRUCTION,
    description=(
        "Provides live stock prices and Google-Search-grounded news, "
        "using Gemini's built-in search tool."
    ),
    tools=[get_stock_price, GoogleSearchTool(bypass_multi_tools_limit=True)],
)
```

**Hey, where's my Claude model?** 🤨

An astute reader will immediately notice that we are not using our Claude model with this agent - instead we now have `model="gemini-3.5-flash-latest"` appearing instead. This isn't incidental; we aren't just showing how easy it is to switch to another LLM with ADK (which is really that easy by the way!). This is infact a fundamental limitation of ADK with internal tools. **Internal tools like Google Search work only on Google's own model-serving infrastructure and cannot be used with non-Gemini models**. If we use `model=get_model("primary")` as we have been doing so far, which points to a Claude model (specifically Claude Haiku), the agent will fail at runtime. We will address this limitation with a custom search function later in this lesson.

Create `agents/lesson04_built_in_tools/__init__.py`:

```python
from . import agent
```

One detail here needs a word of explanation before you run it, especially if you've seen older ADK examples that show search grounding as simply `tools=[google_search]`. That pattern isn't wrong, it's just dated: prior to ADK Python release 1.16 (October 2025), `google_search` genuinely could not be combined with any other tool in the same agent, only one built-in tool, by itself, per agent, so `tools=[google_search]` alone was the only supported shape. `google_search` itself is a ready-made, pre-built instance of the search tool that ADK exports directly, and it's still the simplest way to add search grounding when it's the *only* tool an agent needs. Here, though, we're also giving the agent our custom `get_stock_price` tool, and that's exactly the situation the plain `google_search` singleton doesn't handle. Drop it into this agent's tools list alongside `get_stock_price` and you'd hit an error, not a working two-tool agent!

That's what `GoogleSearchTool(bypass_multi_tools_limit=True)` is for. Instead of using the pre-built `google_search` instance, we construct the underlying `GoogleSearchTool` class ourselves and pass the flag that explicitly opts into combining it with other tools. This flag has been available since ADK 1.16 release, well before ADK 2.0, so this isn't a 2.x-only capability; if you've been working with a recent ADK 1.x codebase, you've had access to this fix the whole time, you just needed to know it existed 😮!

Under the hood, setting the flag causes ADK to run the search as an isolated sub-agent call rather than a true inline model built-in: a separate, hidden model invocation handles the search and hands the result back to the main agent. That raises a fair question: _"if the fix is one keyword argument, why isn't it just the default behavior of `google_search` itself?"_ Because it isn't actually free. That hidden sub-agent call is a genuine extra model invocation, with its own latency and its own token cost, every single time search fires. If Google had made this the default, every existing single-tool search agent out there would have silently started making an extra hidden model call per search, with no code change and no warning, changing everyone's cost and latency profile overnight. You should, in fact, thank Google for this 😊.

**The rule of thumb going forward:** reach for the plain `google_search` singleton when search grounding is the _only tool_ on an agent, and switch to `GoogleSearchTool(bypass_multi_tools_limit=True)` explicitly (knowing you'll incur more token costs!) the moment you need to combine it with anything else, exactly like we're doing here. 

One thing that flag does not change though: it only relaxes the one-built-in-tool-per-agent restriction, not the model restriction, so `GoogleSearchTool`, with or without `bypass_multi_tools_limit`, still works _only with Gemini models_ 🙁. 

Ok, enough of _gyan_. Let's run our agent! Type in the following command(s) from a command prompt:

```bash
# ensure your uv environment is active
source .venv/bin/activate # or .venv\Scripts\activate on Windows
# run the agent
uv run adk run agents/lesson04_built_in_tools
```

Ask about a price:

```
What's Reliance Industries trading at? Ticker is RELIANCE.NS
```

You should see it call `get_stock_price` and come back with a current close price, the previous close, and the percentage move, worded as a short factual statement. I got a response like the following - your's would be different as it's a _live_ price that is displayed. Check on the Yahoo Finance! website that it shows the same values. Mine tallied, so all good!

> [market_briefing_agent]: Reliance Industries Limited (RELIANCE.NS) is trading at **₹1,267.70**, down **-0.96%** (a decrease of ₹12.30) from its previous close of ₹1,280.00.

Then ask about news, in the same session:

```
Why has Tesla's stock been moving this week?
```

You won't see an explicit separate tool call for search the way you did for the price lookup, since grounding happens inside Gemini's own generation process rather than as a visible function call. The answer itself, though, should reflect real, current news with cited sources, not a generic, dated summary.

For the web UI:

```bash
uv run adk web agents
```

Select `lesson04_built_in_tools` and try the same two questions there.

## Built-in tools versus function tools

You just used two different kinds of tool in the same agent, `get_stock_price` and `GoogleSearchTool`, and they work in fundamentally different ways.

A function tool, like `get_stock_price`, is code you write and ADK exposes to the model. A built-in tool is different: it's a capability Google runs internally, on their own servers, as part of generating a response. When you give Gemini the `google_search` built-in tool, Gemini itself performs the search as part of its inference process and folds the results into its answer, you never see a separate "search API call" happening in your code the way you do with a function tool, which is exactly what you just observed: a visible tool call for the price, and no equivalent visible call for the news.

This is also why the agent you just built had to use Gemini models only. Built-in tools are wired into a particular model provider's infrastructure, they're not portable code you can hand to any model. `google_search` is Gemini-only because it depends on machinery inside Google's model-serving stack that simply doesn't exist for Claude. If you're curious what that looks like in practice, try editing this agent's `agent.py` to use `model="claude-haiku-4-5-20251001"` (wrapped in `AnthropicLlm`, as always) while keeping `GoogleSearchTool` in its tools list, then ask it a news question. You should see it fail with an error naming the model as unsupported for Google Search. Revert the change once you've seen it; we're not using this agent with Claude going forward.

That failure is the actual problem for us: Claude is our preferred model, and a Gemini-exclusive tool means Claude-based agents are locked out of grounded, current information unless we build an equivalent ourselves. Function tools have no such restriction, since they're just Python functions ADK calls on your behalf, which is exactly why a custom search function tool is a real, working substitute here, not a workaround with caveats attached. That's what we're building next.

## Step 2: Build a custom search tool and a Claude-based agent

This time we're reaching for Tavily, a search API purpose-built for AI agents rather than for a person scanning a results page. It returns clean, structured results (title, URL, content snippet, relevance score) instead of raw HTML to parse, and it has a search mode aimed specifically at finance-related queries, a good fit for a BFSI series. To use Tavily, you'll need an API key and you'll need to add the Tavily module to our local environment. The API key has quota restructions for free-usage, which are good enough when learning ADK concepts.

**Get a free API key:**

1. Go to [tavily.com](https://tavily.com) and sign up for a free account.
2. Once logged in, your API key is shown on your dashboard, it starts with `tvly-`.
3. Copy it and add it to your project's `.env` file, alongside your existing keys:

```bash
# .env
ANTHROPIC_API_KEY=your-anthropic-key-here
GOOGLE_API_KEY=your-google-api-key-here
GOOGLE_GENAI_USE_VERTEXAI=FALSE
TAVILY_API_KEY=your-tavily-key-here
```

Tavily's free tier gives you a monthly credit allowance that's generous enough for working through this series, but it is metered, unlike other search tools like DuckDuckGo. Keep that in mind if you find yourself re-running this lesson's queries many times over.

**Add the dependency**

Run these commands from a terminal and from the root folder of this project.

```bash
# ensure your uv environment is active
source .venv/bin/activate # or .venv\Scripts\activate on Windows
# add dependency
uv add tavily-python
```

Add a second function to `agents/common/finance_tools.py`, alongside `get_stock_price`.

```python
import os

from tavily import TavilyClient


def get_stock_news(company_or_ticker: str, max_results: int = 5) -> dict:
    """Searches the web for recent news about a company or stock.

    This is a provider-agnostic alternative to ADK's built-in
    google_search tool. It works with any model, including Claude,
    since it's a plain function tool rather than a model built-in.
    Uses Tavily, a search API purpose-built for AI agents, with its
    finance-specific search mode for more relevant results.

    Args:
        company_or_ticker: The company name or ticker symbol to search news for, e.g. "Tata Motors" or "TSLA".
        max_results: Maximum number of news results to return.
            Defaults to 5.

    Returns:
        A dict with a list of articles, each containing a title,
        short snippet, and the source URL.
    """
    try:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return {
                "found": False,
                "query": company_or_ticker,
                "error": "TAVILY_API_KEY is not set in the environment.",
            }

        client = TavilyClient(api_key=api_key)
        query = f"{company_or_ticker} stock news"
        response = client.search(
            query=query,
            max_results=max_results,
            topic="finance",
        )

        articles = [
            {
                "title": r.get("title", ""),
                "snippet": r.get("content", ""),
                "url": r.get("url", ""),
            }
            for r in response.get("results", [])
        ]
        return {"found": bool(articles), "query": query, "articles": articles}
    except Exception as error:
        return {"found": False, "query": company_or_ticker, "error": str(error)}
```

We use the same defensive pattern as `get_stock_price`: every failure path returns a structured dict rather than raising, so a bad or empty search doesn't crash the agent turn.

Now build the Claude-side agent. **NOTE** - this is created in a separate folder than the Google agent - don't create in same folder! 

Create `agents/lesson04_market_briefing/agent.py`:

```python
"""
Lesson 4: Built-in Tools (Claude variant).

The same market briefing agent, but running on Claude. Live prices
still come from get_stock_price; current news now comes from
get_stock_news, a function tool wrapping the Tavily search API,
standing in for the built-in google_search tool Claude can't use.
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

Structurally, there's nothing new in this file if you've done Lesson 3: two function tools, both imported from the shared `common` package. The instruction is worth reading closely, though. It tells the model explicitly to cite sources and include URLs for news, and to decline giving investment advice. Neither of those behaviors happens automatically. A model asked "why did this stock move" will happily generate a plausible-sounding explanation without a source unless told to ground its answer in what the tool actually returned, and a model asked "should I buy this stock" will often just answer unless it's told that's out of scope. In a BFSI context, both of these are the kind of thing that turns into a compliance problem if left to the model's default behavior.

## Step 3: Compare both agents on the same prompts

```bash
uv run adk web agents
```

You'll now see both agents in the dropdown: `lesson04_market_briefing` (Claude) and `lesson04_built_in_tools` (Gemini). Ask both the same two questions.

Price:

```
What's Reliance Industries trading at? Ticker is RELIANCE.NS
```

Both should call `get_stock_price` and return matching figures, since they're pulling from the same data source regardless of which model is asking.

Here is what I saw when I selected `lesson04_market_briefing` (with Claude model)

<div aligh="center">
    <image src="images/what_is_reliance_tradingat_claude.png" alt="Reliance Price (Claude)"/>
</div>

**NOTE:** this is a live price quote, thanks to our 
`get_stock_price` tool. Numbers you'll see will most certainly be different from mine!

News:

```
Why has Tesla's stock been moving this week?
```

<div aligh="center">
    <image src="images/why_tesla_stock_moved_claude.png" alt="Tesla Price Move (Claude)"/>
</div>

This is where they are most likely to diverge in mechanism, even though the outcome looks similar from the outside. On the Claude agent, you'll see an explicit `get_stock_news` tool call, followed by a summary with source URLs pulled from Tavily. On the Gemini agent, there's no equivalent visible tool call, the search happens inside Gemini's own generation process, but the final answer should similarly reflect current news with cited sources, this time from Google's own grounding. The specific articles referenced will likely differ between the two, since they're drawing from different search backends, but both should be grounded in real, current information rather than a generic, dated summary, which is the actual bar we set out to clear in this lesson.

Now I got cheecky and asked

```
Should I buy Tesla?
```

<div aligh="center">
    <image src="images/should_I_buy_tesla.png" alt="Buy Tesla (Claude)"/>
</div>


This behavior is consistent with the prompt (`instruction`) we gave our agent - don't give advise!


## If you're coming from LangChain or LangGraph

LangChain has an equivalent split, though it draws the line slightly differently. Provider-hosted capabilities, like OpenAI's hosted web search or code interpreter tools, work only with that provider's models, the same restriction we just hit with `google_search` and Gemini. Anything you'd build with a `Tool` or `@tool`-decorated function in LangChain, wrapping a search API, a database call, or any external service yourself, is portable across whatever model you point LangChain at, exactly like `get_stock_news` here. If you've previously reached for a search API wrapper in LangChain rather than a provider's built-in browsing tool for portability reasons, you already understand the trade-off this lesson just walked through. Tavily specifically may already be familiar if you've worked with LangChain or LangGraph before: it's the search tool their own official tutorials and quickstarts default to, so this lesson's `get_stock_news` is a plain ADK function tool doing the same job you may already associate with `TavilySearch` or `langchain-tavily` in that ecosystem.

## A word on cost

Stock price lookups via `yfinance` are free and don't touch your LLM token budget at all, they're a direct data fetch, not a model call. Tavily search runs on its free tier's monthly credit allowance, comfortable for working through this lesson and re-testing a few times, but it is metered, unlike an unofficial wrapper with no formal limits, so keep an eye on your usage on Tavily's dashboard if you're running this lesson's queries repeatedly; for production BFSI use, you'd size a paid Tavily plan, or an equivalent licensed news/search API, to your actual query volume. On the model side, each of these questions costs one or two Claude Haiku exchanges, still a fraction of a cent. The Gemini variant's grounded search, when `bypass_multi_tools_limit` triggers its sub-agent call, uses one extra Gemini call per search, still comfortably inside Gemini Flash's free tier for this kind of testing volume.

## Conclusion

Whew! That concludes a rather long, and dare I say _tedious_ in some places, lesson. 

In this lesson, we gave an agent access to current information from beyond its training data, first the native way, using Gemini's built-in `google_search` | `GoogleSearchTool(...)` tool, and then a portable way, using a free function tool that gets Claude to the same outcome. Along the way, we saw exactly why `google_search` is Gemini-only (it runs inside Google's own model-serving infrastructure, not as portable code) and built a genuine substitute rather than working around the limitation. Since Claude is this series' default, having a working, non-Gemini path to grounded, cited answers means the model policy from the series introduction holds up even for a capability ADK markets as Gemini-exclusive.

In the next lesson we move from tools to output. Every agent so far has answered in free-form text, fine for a chat window, but not for feeding a result into another system. We'll build a credit risk scoring agent for a retail bank's underwriting desk that returns a validated, fixed-shape JSON verdict every time, using ADK's structured output support, combined with the same kind of tool-calling we've used since Lesson 3.
