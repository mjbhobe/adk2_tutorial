"""
Lesson 4: Built-in Tools & Grounding (Gemini variant).

A market briefing agent for an investment research desk, using
Gemini's built-in google_search tool for news grounding alongside a
function tool for live stock prices.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
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
    model="gemini-3.5-flash-lite", # "gemini-flash-latest",
    instruction=AGENT_INSTRUCTION,
    description=(
        "Provides live stock prices and Google-Search-grounded news, "
        "using Gemini's built-in search grounding tool."
    ),
    tools=[get_stock_price, GoogleSearchTool(bypass_multi_tools_limit=True)],
)
