"""Lesson 16a: what happens with more than one terminal node.

Every graph in Lesson 16 and earlier in this lesson converged back to
one final node after a branch. That is not required. A graph can end
in two, or more, genuinely different places, with nothing after them.

This tiny example proves what happens when it does: only the branch
that actually ran produces a result, and `events[-1].output` reflects
exactly that branch, correctly, whichever one it was.
"""

from __future__ import annotations

import asyncio

from google.adk.workflow import START, Workflow, node
from google.adk.runners import InMemoryRunner


@node
async def route_request(ctx, node_input: str) -> str:
    """Routes purely on the input string itself, for a minimal example."""
    print(f"  [route_request] routing on: {node_input}")
    ctx.route = node_input
    return node_input


@node
async def handle_as_a(node_input: str) -> str:
    print("  [handle_as_a] node running")
    return f"Path A handled: {node_input}"


@node
async def handle_as_b(node_input: str) -> str:
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
    runner = InMemoryRunner(agent=two_terminal_workflow)

    for choice in ("a", "b"):
        events = await runner.run_debug(choice, quiet=True)
        print(f"input={choice!r} -> events[-1].output = {events[-1].output!r}\n")


if __name__ == "__main__":
    asyncio.run(main())
