"""
Lesson 4: Built-in Tools & Grounding (Claude variant).

The same market briefing agent, but running on Claude. Live prices
still come from get_stock_price; current news now comes from
get_stock_news, a function tool wrapping the Tavily search API,
standing in for the built-in google_search tool Claude can't use.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
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
