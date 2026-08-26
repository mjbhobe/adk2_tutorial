"""
Lesson 16a: standalone multi-terminal-node example

Shows what happens when a graph ends in more than one place, with no
node after either branch to converge on.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import asyncio

from google.adk.workflow import START, Workflow, node
from google.adk.runners import InMemoryRunner


@node
async def route_request(ctx, node_input: str) -> str:
    """Routes purely on the input string itself, for a minimal example.

    Args:
        ctx: The node's execution context. Used to set ctx.route.
        node_input: The raw route choice, "a" or "b".

    Returns:
        The same string, unchanged.
    """
    print(f"  [route_request] routing on: {node_input}")
    ctx.route = node_input
    return node_input


@node
async def handle_as_a(node_input: str) -> str:
    """Terminal node for route "a".

    Args:
        node_input: The value routed here.

    Returns:
        A short confirmation string.
    """
    print("  [handle_as_a] node running")
    return f"Path A handled: {node_input}"


@node
async def handle_as_b(node_input: str) -> str:
    """Terminal node for route "b".

    Args:
        node_input: The value routed here.

    Returns:
        A short confirmation string.
    """
    print("  [handle_as_b] node running")
    return f"Path B handled: {node_input}"


two_terminal_workflow = Workflow(
    name="two_terminal_workflow",
    edges=[
        (START, route_request),
        (route_request, {"a": handle_as_a, "b": handle_as_b}),
    ],
)
# No node after handle_as_a or handle_as_b. Both are terminal.


async def main() -> None:
    """Runs the graph twice, once per route, and prints each result."""
    runner = InMemoryRunner(agent=two_terminal_workflow)

    for choice in ("a", "b"):
        events = await runner.run_debug(choice, quiet=True)
        print(f"input={choice!r} -> events[-1].output = {events[-1].output!r}\n")


if __name__ == "__main__":
    asyncio.run(main())
