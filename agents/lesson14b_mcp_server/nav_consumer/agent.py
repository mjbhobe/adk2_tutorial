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
