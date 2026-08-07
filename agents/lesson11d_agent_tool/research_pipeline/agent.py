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
    model=get_model("primary"),  # Claude!
    description="Answers questions, using a Google Search specialist for anything needing current information.",
    instruction=instruction,
    # which can now use google_search 😌
    tools=[AgentTool(agent=search_specialist_agent)],
)
