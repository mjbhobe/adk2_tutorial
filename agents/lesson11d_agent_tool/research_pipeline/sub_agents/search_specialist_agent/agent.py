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
