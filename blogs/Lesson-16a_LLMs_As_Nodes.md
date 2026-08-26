# Lesson 16a: LLMs As Nodes

The previous lesson introduced `Workflow` as a way to build clear and controlled graph-based processes. Unlike a single LLM agent that decides every step, a workflow makes the process explicit and traceable. We covered its main components: `nodes`, `edges`, `graphs`, and the `Workflow` that runs them. We also used the `InMemoryRunner.run_debug(...)` convenience function to test our workflows.

We built two workflow patterns: A `sequential workflow`, which runs nodes in a fixed serial order, and a `branching workflow` uses business logic to choose between different paths and then join them again. We also saw how `node_input` passes data between nodes, how `ctx.route` is used to decide which branch to traverse next, and how `ctx.state` shares data across the graph. For all nodes of these workflows, we used deterministic functions annotated with the `@node` decorator. Deterministic functions as nodes worked here because each node performed a definate mathematical calculations or routing.

However, some steps cannot be written as a deterministic functions. Continuing from our _loan processing_ example from the previous lesson: Take the message that needs to go back to the customer once a loan disbursal decision is made. Whether it's `auto-cleared` or `pending review`, someone still has to explain that decision in plain language, reassuring but honest, and there is no formula for that. That step needs _judgment_ and _text generation_, an LLM's core capability, not a fixed rule. An ADK `Agent` slots in perfectly into the workflow for such a type of task!

## What this lesson covers

This lesson shows you how an `Agent` can be used as a node in a `Workflow`, wired in exactly the same way as any function node we saw in the previous lesson. We will extend the loan disbursement graph from Lesson 16 by adding an _Agent node_ that composes the final note that goes out to the customer.

### Part 1: Dropping an Agent into a graph

An `Agent` can work as a node, because it's derived from `BaseNode`. Unlike a function, it **does not** require the `@node` decorator - a simple Python function needed the decorator to _convert_ it to a `BaseNode`. Adding an `Agent` to a workflow is no different than adding a function. Let's see how.

Suppose we define a `draft_notification` agent like this in some `agent.py` file in our directory structure. You should be familiar with this code by now:

```python
# partial contents of agent.py file
from google.adk.agents import Agent
from common.model_config import get_model

from .tools import ....


INSTRUCTION = """
.... agents instructions
"""

draft_notification = Agent(
    name="draft_notification",
    description="Drafts a notfication email...",
    model=get_model("primary"),
    instruction=INSTRUCTION,
    tools=[...],
    ...
)
```

And here's how we could define the workflow:

```python
# in the file where we define the workflow
from ... import draft_notification 

my_workflow = Workflow(
    name="my_workflow_name",
    edges=[(START, calculate_deductions, draft_notification)],
)
```

The `edges` line is exactly the same as we have used in the sequential workflow example in Lesson 16. `draft_notification` just happens to be an `Agent`. `calculate_deductions` could be an annotated Python function (`@node`).

**There is one thing to decide, though**: how the agent behaves as a node. `Agent` has a `mode` field with three values, `chat`, `single_turn`, and `task`.

- **`chat`**: is for multi-agent transfer scenarios, not something a graph node needs, so this lesson leaves it alone entirely.
- **`single_turn`**: the _agent node_ receives its input, the model replies once, and that reply is the node's output. One exchange, done.
- **`task`**: the _agent node_ can call tools across several rounds, deciding for itself how many rounds it needs, and only finishes when it explicitly says so.

> 📌 **NOTE**: `single_turn` is the default value for the `mode` attrubute of the `Agent`. So you don't have to set it explicitly (as we have done, or not done, here!).
>
> Conversely, `task` mode has to be set explicitly, since a node that can run for several rounds is a bigger commitment than one that replies once.

### Part 2: using Agent in single_turn mode

We'll build functionality to draft & dispatch a message to the customer. This should happen after the disbursement decision is done in the `Workflow` we have already developed in the previous lesson.

Technically, this will mean adding two new nodes after the `log_decision` node of the previous workflow. Everything before `log_decision` is unchanged from Lesson 16.

We'll be adding the following nodes:

* a `draft_notification` node, which is an _Agent node_ that writes the customer-facing message for the loan decision, and
* a `dispatch_notification` node, which is a plain _function node_ that _sends the message_. Of course, we won't be actually sending the message. In our case, this node acts like the last node in the graph.

We'll have `draft_notification` (the _Agent node_) return _structured_ data - an email subject and the body - not a paragraph of loosely shaped text. We know how to handle this right? Yes, we'll use the `output_schema` of the `Agent` and we'll define the structure using a Pydantic model - we did this way back in Lesson 5. What is new here is what this one field does inside a graph: it shapes what the model is asked to produce, and it validates the node's output for the graph, both at once.

**Setup the folder structure.**

```
adk2_tutorial/
└── agents/
    └── lesson16a_llm_nodes/
        ├── draft_notification/
        │   ├── __init__.py
        │   └── agent.py
        ├── workflow.py
        ├── __init__.py
        └── main.py
```

**Code listings.**

Create the `draft_notification` package.

`agents/lesson16a_llm_nodes/draft_notification/__init__.py`

```python
from . import agent
```

Define the agent itself and the schema it must return.

`agents/lesson16a_llm_nodes/draft_notification/agent.py`

```python
"""
Lesson 16a: the draft_notification agent

Defines the structured output schema and the single_turn Agent that
drafts the customer-facing message for a loan decision.
"""

from pydantic import BaseModel

from google.adk.agents import Agent

from common.model_config import get_model


class NotificationMessage(BaseModel):
    """The structured shape draft_notification_agent must return.

    Attributes:
        subject: A short subject line for the notification.
        body: The full message body, plain language.
    """

    subject: str
    body: str


_INSTRUCTION = """You are a loan operations assistant.
You will receive a JSON object describing a loan decision, with keys
`net_disbursement` and `status`. `status` is either `AUTO_DISBURSED` or
`PENDING_MANUAL_REVIEW`.

Write a short customer-facing notification about this decision. Keep
the tone plain and reassuring, no jargon. If the status is
`AUTO_DISBURSED`, confirm the amount and that funds are on the way.
If it is `PENDING_MANUAL_REVIEW`, explain that the loan needs a quick
compliance check before funds move, without alarming the customer.
"""

draft_notification_agent = Agent(
    name="draft_notification_agent",
    model=get_model("primary"),
    description="Drafts a structured customer notification for a loan decision.",
    instruction=_INSTRUCTION,
    output_schema=NotificationMessage,
)
# No mode= set here on purpose. A standalone Agent used directly as a
# workflow node, with no parent agent, defaults to mode='single_turn'.
```

`output_schema` is doing two jobs in this file. It shapes what the model is asked to produce, and it validates the node's output for the graph. One field, both jobs, by design.

One thing worth being precise about: `node_input` for an `Agent` node is not validated against a schema the way `node_input` on a function node can be. Whatever you pass in becomes the literal message sent to the model, a dict gets turned into a JSON string, a string is used as is. `Agent` does have its own `input_schema` field, but its actual job is different, it shapes the schema for when this agent is used as a tool by another agent, not the shape of `node_input` here. That is why `_INSTRUCTION` above spells out the expected JSON shape in plain English, that is genuinely how the model finds out what it is looking at.

Now the function nodes and the graph itself.

`agents/lesson16a_llm_nodes/workflow.py`

```python
"""
Lesson 16a: the loan disbursement workflow

All function nodes and the Workflow that wires them together, plus
the draft_notification agent node imported from its own subfolder.
Everything through log_decision is unchanged from Lesson 16.
"""

import json
from typing import Any

from google.adk.workflow import START, Workflow, node

from draft_notification.agent import draft_notification_agent


@node
async def calculate_deductions(ctx: Any, node_input: str) -> dict:
    """Parses the incoming loan request and works out fee plus tax.

    Args:
        ctx: The node's execution context. Unused here.
        node_input: A JSON string with loan_amount, fee_percentage,
            and gst_rate.

    Returns:
        A dict with loan_amount and total_deductions.
    """
    params = json.loads(node_input)
    loan_amount = params["loan_amount"]
    fee_percentage = params["fee_percentage"]
    gst_rate = params["gst_rate"]

    base_fee = loan_amount * (fee_percentage / 100)
    tax = base_fee * (gst_rate / 100)
    total_deductions = base_fee + tax

    print(
        f"  [calculate_deductions] base_fee={base_fee}, tax={tax}, "
        f"total_deductions={total_deductions}"
    )
    return {"loan_amount": loan_amount, "total_deductions": total_deductions}


@node
async def calculate_net_payout(ctx: Any, node_input: dict) -> dict:
    """Works out what the borrower actually receives.

    Args:
        ctx: The node's execution context. Unused here.
        node_input: The dict returned by calculate_deductions.

    Returns:
        A dict with net_disbursement and a starting status.
    """
    loan_amount = node_input["loan_amount"]
    total_deductions = node_input["total_deductions"]
    net_disbursement = loan_amount - total_deductions

    result = {"net_disbursement": net_disbursement, "status": "READY_FOR_TRANSFER"}
    print(f"  [calculate_net_payout] {result}")
    return result


@node
async def check_compliance_threshold(
    ctx: Any, node_input: dict, manual_review_limit: float
) -> dict:
    """Decides whether this payout needs a human to sign off on it.

    Args:
        ctx: The node's execution context. Used to set ctx.route.
        node_input: The dict returned by calculate_net_payout.
        manual_review_limit: Read from ctx.state["manual_review_limit"].

    Returns:
        The same dict it received, unchanged.
    """
    net_disbursement = node_input["net_disbursement"]
    print(
        f"  [check_compliance_threshold] net_disbursement={net_disbursement}, "
        f"manual_review_limit={manual_review_limit}"
    )

    if net_disbursement > manual_review_limit:
        ctx.route = "needs_review"
    else:
        ctx.route = "auto_clear"

    return node_input


@node
async def flag_for_review(node_input: dict) -> dict:
    """Marks a payout as held for manual compliance review.

    Args:
        node_input: The dict carried over from check_compliance_threshold.

    Returns:
        The same dict with status updated.
    """
    node_input["status"] = "PENDING_MANUAL_REVIEW"
    return node_input


@node
async def auto_disburse(node_input: dict) -> dict:
    """Marks a payout as cleared for automatic disbursement.

    Args:
        node_input: The dict carried over from check_compliance_threshold.

    Returns:
        The same dict with status updated.
    """
    node_input["status"] = "AUTO_DISBURSED"
    return node_input


@node
async def log_decision(node_input: dict) -> dict:
    """The point both branches converge on.

    Args:
        node_input: The dict from either branch.

    Returns:
        The same dict, unchanged. Becomes node_input for
        draft_notification_agent next.
    """
    print(f"  [log_decision] final decision: {node_input}")
    return node_input


@node
async def dispatch_notification(node_input: dict) -> dict:
    """Receives the drafted notification and finalizes the result.

    Args:
        node_input: {"subject": ..., "body": ...}, the validated
            output of draft_notification_agent.

    Returns:
        The same dict, unchanged. This is the graph's terminal node.
    """
    print(f"  [dispatch_notification] subject: {node_input['subject']}")
    print(f"  [dispatch_notification] body: {node_input['body']}")
    return node_input


loan_disbursement_workflow = Workflow(
    name="loan_disbursement_workflow",
    edges=[
        (START, calculate_deductions, calculate_net_payout, check_compliance_threshold),
        (check_compliance_threshold, {"needs_review": flag_for_review, "auto_clear": auto_disburse}),
        (flag_for_review, log_decision),
        (auto_disburse, log_decision),
        (log_decision, draft_notification_agent, dispatch_notification),
    ],
)

root_agent = loan_disbursement_workflow
```

`node_input` here for `dispatch_notification` is the dict `draft_notification_agent` returned, already validated against `NotificationMessage`. Nothing about this function is different from any function node in Lesson 16, an `Agent` node's validated output flows to the next node exactly like a function node's return value does.

The package marker for this lesson folder, needed for `adk web agents` discovery.

`agents/lesson16a_llm_nodes/__init__.py` - **leave this blank!**

And the driver.

`agents/lesson16a_llm_nodes/main.py`

```python
"""
Lesson 16a: driver for the loan disbursement workflow

Runs the extended loan disbursement graph for two loan amounts, one
that clears automatically and one that trips manual review.

Needs a real, working model configured in common/model_config.py to
actually run. The loan numbers are deterministic. The notification
text is not, it is genuine model output, so do not expect the exact
wording shown in the lesson.
"""

import asyncio
import json

from google.adk.runners import InMemoryRunner

from workflow import loan_disbursement_workflow


async def run_loan(runner: InMemoryRunner, session_id: str, loan_amount: float) -> None:
    """Seeds session state, runs the graph once, and prints the result.

    Args:
        runner: The shared InMemoryRunner wrapping the workflow.
        session_id: A unique session id for this run.
        loan_amount: The loan principal to test with.
    """
    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id="lesson16a_user",
        session_id=session_id,
        state={"manual_review_limit": 1_000_000},
    )

    payload = json.dumps(
        {"loan_amount": loan_amount, "fee_percentage": 2.0, "gst_rate": 18.0}
    )

    events = await runner.run_debug(
        payload, quiet=True, session_id=session_id, user_id="lesson16a_user"
    )

    print(f"loan_amount={loan_amount} -> {events[-1].output}\n")


async def main() -> None:
    """Runs the graph for two different loan amounts."""
    runner = InMemoryRunner(agent=loan_disbursement_workflow)

    print("Run 1: a loan that clears automatically")
    await run_loan(runner, session_id="run_1", loan_amount=50_000)

    print("Run 2: a loan that trips manual review")
    await run_loan(runner, session_id="run_2", loan_amount=5_000_000)


if __name__ == "__main__":
    asyncio.run(main())
```

**Run the code.**

Start a new terminal and from the project root folder (`adk2_tutorial`) run the following commands:

```bash
# activate your local environment
source .venv/bin/activate
# run the program
uv run agents/lesson16a_llm_nodes/main.py
```

This needs a real, working model behind `get_model("primary")` in `common/model_config.py` to actually run. The loan numbers stay exactly as deterministic as Lesson 16, base fee 1000, tax 180, net payout 48820 for a 50,000 loan. The notification text will not be deterministic, it is genuine model output, so do not expect to see the exact wording shown anywhere in this lesson reproduced on your own run. `subject` and `body` will always be present, `output_schema` guarantees that much, it does not and should not guarantee the wording.

## Part 3: task mode

**What we are building.** A small, separate example, not wired into the loan graph. An agent that decides whether a loan in manual review qualifies for a grace period, by calling a tool to check eligibility before deciding. `grace_period_agent` gets its own subfolder, same convention as `draft_notification_agent`, and since this agent uses a tool, its folder also gets a `tools.py`.

single_turn is one exchange. `task` mode is for a node that may need more than one, calling tools, seeing their results, calling more tools, for as many rounds as the model decides it needs. What ends a `task`-mode node is not a fixed number of rounds, it is an explicit signal. ADK attaches a tool called `finish_task` to every `task`-mode agent automatically, you never add it yourself. The model calls it when it is genuinely done, passing its final answer as that tool's arguments, shaped by the agent's `output_schema`. Whatever the model passes to `finish_task` becomes the node's output.

**Setup the folder structure.**

```
adk2_tutorial/
└── agents/
    └── lesson16a_llm_nodes/
        ├── grace_period/
        │   ├── __init__.py
        │   ├── agent.py
        │   └── tools.py
        └── task_mode_example.py
```

**Code listings.**

Create the `grace_period` package.

`agents/lesson16a_llm_nodes/grace_period/__init__.py`

```python
"""
Lesson 16a: package marker for the grace_period agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from . import agent
```

The tool this agent calls.

`agents/lesson16a_llm_nodes/grace_period/tools.py`

```python
"""
Lesson 16a: tools for the grace_period agent

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""


def lookup_grace_period(loan_status: str) -> dict:
    """Looks up whether a loan in this status can get a grace period.

    A plain function tool, the same kind Lesson 3 covered. Deterministic
    and synthetic, not a real lending policy lookup.

    Args:
        loan_status: The loan's current status, e.g.
            "PENDING_MANUAL_REVIEW".

    Returns:
        A dict with eligible and max_days.
    """
    if loan_status == "PENDING_MANUAL_REVIEW":
        return {"eligible": True, "max_days": 15}
    return {"eligible": False, "max_days": 0}
```

The agent itself.

`agents/lesson16a_llm_nodes/grace_period/agent.py`

```python
"""
Lesson 16a: the grace_period agent

Defines the structured output schema and the task-mode Agent that
decides whether a loan qualifies for a grace period.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from pydantic import BaseModel

from google.adk.agents import Agent

from common.model_config import get_model
from .tools import lookup_grace_period


class GracePeriodDecision(BaseModel):
    """The structured shape grace_period_agent must finish with.

    Attributes:
        eligible: Whether the loan qualifies for a grace period.
        extension_days: The number of days granted, 0 if not eligible.
    """

    eligible: bool
    extension_days: int


_INSTRUCTION = """You are a loan operations assistant.
You will receive a loan's status. Call `lookup_grace_period` with that
status to check eligibility, then decide the final extension in days.
Call `finish_task` once you have decided, do not just describe your
answer in text.
"""

grace_period_agent = Agent(
    name="grace_period_agent",
    model=get_model("primary"),
    description="Decides whether a loan qualifies for a grace period.",
    instruction=_INSTRUCTION,
    tools=[lookup_grace_period],
    mode="task",
    output_schema=GracePeriodDecision,
)
# mode has to be set explicitly here. Unlike a standalone Agent node,
# which defaults to single_turn, task mode is never assumed for you.
```

`mode="task"` is not optional to state here, this is the one place in this lesson where you have to ask for the behavior explicitly. `lookup_grace_period` is a plain function tool, nothing new about tool-calling itself. What is new is that the agent calling it is running as a graph node, and the graph waits for the whole multi-round exchange, tool call, tool result, then `finish_task`, before treating the node as complete.

And the standalone script that runs it.

`agents/lesson16a_llm_nodes/task_mode_example.py`

```python
"""
Lesson 16a: standalone task-mode example

A small, self-contained example separate from the loan disbursement
workflow. Shows a task-mode agent calling a tool across two rounds
before signaling completion through finish_task.

Needs a real, working model configured in common/model_config.py to
actually run.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import asyncio

from google.adk.workflow import START, Workflow
from google.adk.runners import InMemoryRunner

from grace_period.agent import grace_period_agent

grace_period_workflow = Workflow(
    name="grace_period_workflow",
    edges=[(START, grace_period_agent)],
)


async def main() -> None:
    """Runs the grace-period task-mode agent once and prints the result."""
    runner = InMemoryRunner(agent=grace_period_workflow)
    events = await runner.run_debug("PENDING_MANUAL_REVIEW", quiet=True)
    print("Final result:", events[-1].output)


if __name__ == "__main__":
    asyncio.run(main())
```

**Run the code.**

Start a new terminal and from the project root folder (`adk2_tutorial`) run the following commands:

```bash
# activate your local environment
source .venv/bin/activate
# run the program
uv run agents/lesson16a_llm_nodes/task_mode_example.py
```

Same requirement as Part 2, this needs a real model behind `get_model("primary")`. `lookup_grace_period`'s eligibility numbers are synthetic, not a real lending policy. Expect `Final result: {'eligible': True, 'extension_days': 15}` for a `PENDING_MANUAL_REVIEW` loan, the exact `extension_days` figure is the model's own decision within what `lookup_grace_period` told it, so treat 15 as the expected shape, not a guaranteed exact number.

The deep version of this, an agent whose tools are themselves other agents, delegating work across a whole team rather than calling one plain function, is Lesson 16e's job, not this one. What you have here is task mode's core mechanic, working, on its own.

## Part 4: more than one terminal node

**What we are building.** Every graph so far, in this lesson and in Lesson 16, converged back to a single node after branching. That is not a requirement. This example shows a graph that ends in two genuinely different places, with nothing after either one. No agent involved here, this is purely about the graph mechanics.

**Setup the folder structure.**

```
adk2_tutorial/
└── agents/
    └── lesson16a_llm_nodes/
        └── multi_terminal_example.py
```

**Code listing.**

`agents/lesson16a_llm_nodes/multi_terminal_example.py`

```python
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
```

**Run the code.**

Start a new terminal and from the project root folder (`adk2_tutorial`) run the following commands:

```bash
# activate your local environment
source .venv/bin/activate
# run the program
uv run agents/lesson16a_llm_nodes/multi_terminal_example.py
```

No model needed for this one, it is pure function nodes, so it runs the same way every time:

```
  [route_request] routing on: a
  [handle_as_a] node running
input='a' -> events[-1].output = 'Path A handled: a'

  [route_request] routing on: b
  [handle_as_b] node running
input='b' -> events[-1].output = 'Path B handled: b'
```

Whichever branch actually fired is the one `events[-1].output` reflects, correctly, every time. A graph with more than one ending is not a special case you need to guard against, `run_debug` already handles it exactly the way you would want it to.

## Complete folder structure for this lesson

```
adk2_tutorial/
└── agents/
    └── lesson16a_llm_nodes/
        ├── draft_notification/
        │   ├── __init__.py
        │   └── agent.py
        ├── grace_period/
        │   ├── __init__.py
        │   ├── agent.py
        │   └── tools.py
        ├── workflow.py
        ├── __init__.py
        ├── main.py
        ├── task_mode_example.py
        └── multi_terminal_example.py
```

## What's next

This lesson put judgment inside a graph one node at a time. Lesson 16b turns to the graph's own shape: what makes a graph valid in the first place, and what happens when a `Workflow` is nested as a node inside another `Workflow`, a graph of graphs, along with `max_concurrency`, the control over how much of a graph is allowed to run at once.
