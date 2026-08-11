"""Lesson 14a: Two agents, one plain MCP consumer, one skill-gated.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

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
    model=get_model("primary"),
    description="Answers questions about Stripe account data using every available Stripe MCP tool directly.",
    instruction=research_instruction,
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
