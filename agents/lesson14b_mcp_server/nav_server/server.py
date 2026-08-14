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
