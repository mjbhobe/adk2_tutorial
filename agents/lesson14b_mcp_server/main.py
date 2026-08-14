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
