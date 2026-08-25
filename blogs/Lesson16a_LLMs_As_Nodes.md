# Lesson 16a: LLMs As Nodes

The previous lesson introduced `Workflow` as a way to build clear and controlled graph-based processes. Unlike a single LLM agent that decides every step, a workflow makes the process explicit and traceable. We covered its main components: `nodes`, `edges`, `graphs`, and the `Workflow` that runs them.

We built two workflow patterns: A `sequential workflow`, which runs nodes in a fixed serial order, and a `branching workflow` uses business logic to choose between different paths and then join them again. We also saw how `node_input` passes data between nodes and how `ctx.state` shares data across the graph. For all nodes of these workflows, we used deterministic functions annotated with the `@node` decorator. Deterministic functions as noded worked here because each node performed a definate mathematical calculations or routing.

However, some steps cannot be written as a deterministic functions. Take the message that needs to go back to the customer once a decision is made. `auto-cleared` or `pending review`, someone still has to explain that decision in plain language, reassuring but honest, and there is no formula for that. That step needs judgment and text generation, an LLM's core capability, not a fixed rule. An ADK `Agent` is built for exactly this and it can work as a node in a workflow!

## What this lesson covers

This lesson shows you how an `Agent` can be a node in a `Workflow`, wired in exactly the same way as any function node we saw in the previous lesson, with edges pointing in and out of it like any other node. We will extend the loan disbursement graph from Lesson 16 by adding an _Agent node_ that composes the final note that goes out to the customer.

## Part 1: Dropping an Agent into a graph

An `Agent` needs no `@node` decorator. Lesson 16 mentioned that a node can wrap a plain function, an `Agent`, or even another `Workflow`, without saying why that last one works. Here is why: `Workflow` is itself a `BaseNode` under the hood, and so is `Agent`. Anywhere the graph accepts a node, it accepts anything built on `BaseNode`, no special casing needed.

Dropping an `Agent` into a workflow is very simple. Just add the variable that points to the Agent into the workflow. Suppose we define a `draft_notification` agent like this, in some `agent.py` file in our directory structure as we have been doing so far:

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

The above definition is one we should be intimately familiar with by now.

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

If you do not set `mode` at all in the `Agent`'s definition (as we have done here), it defaults to `single_turn`. You never have to ask for the simple case. `task` mode, on the other hand, always has to be requested explicitly, since a node that can run for several rounds is a bigger commitment than one that replies once.

## Part 2: single_turn mode

**What we are building.** Two new nodes after `log_decision`, `draft_notification` and `dispatch_notification`. `draft_notification` is an `Agent` that writes the customer-facing message for a loan decision. `dispatch_notification` is a plain function node that receives that message and finishes the graph. Everything before `log_decision` is unchanged from Lesson 16.

**The schema.** `draft_notification` has to return something predictable, a subject and a body, not a paragraph of loosely shaped text. That is what `output_schema` is for, and you have already used a Pydantic model for structured output back in Lesson 5. What is new here is what this one field does inside a graph: it shapes what the model is asked to produce, and it validates the node's output for the graph, both at once.

```python
from pydantic import BaseModel

class NotificationMessage(BaseModel):
    subject: str
    body: str
```

**The node.**

```python
from google.adk.agents import Agent
from common.model_config import get_model

_draft_notification_instruction = """You are a loan operations assistant.
You will receive a JSON object describing a loan decision, with keys
`net_disbursement` and `status`. `status` is either `AUTO_DISBURSED` or
`PENDING_MANUAL_REVIEW`.

Write a short customer-facing notification about this decision. Keep
the tone plain and reassuring, no jargon. If the status is
`AUTO_DISBURSED`, confirm the amount and that funds are on the way.
If it is `PENDING_MANUAL_REVIEW`, explain that the loan needs a quick
compliance check before funds move, without alarming the customer.
"""

draft_notification = Agent(
    name="draft_notification",
    model=get_model("primary"),
    description="Drafts a structured customer notification for a loan decision.",
    instruction=_draft_notification_instruction,
    output_schema=NotificationMessage,
)
```

No `mode=` here, on purpose, this is the standalone-default case from Part 1.

One thing worth being precise about, since it is easy to assume the wrong way: `node_input` for an `Agent` node is not validated against a schema the way `node_input` on a function node can be. Whatever you pass in becomes the literal message sent to the model, a dict gets turned into a JSON string, a string is used as is. `Agent` does have its own `input_schema` field, but its actual job is different, it shapes the schema for when this agent is used as a tool by another agent, not the shape of `node_input` here. So the instruction above spells out the expected JSON shape in plain English, because that is genuinely how the model finds out what it is looking at, not through a validated schema on the way in.

**The next node.**

```python
@node
async def dispatch_notification(node_input: dict) -> dict:
    print(f"  [dispatch_notification] subject: {node_input['subject']}")
    print(f"  [dispatch_notification] body: {node_input['body']}")
    return node_input
```

`node_input` here is the dict `draft_notification` returned, already validated against `NotificationMessage`. Nothing about this function is different from any function node in Lesson 16, an `Agent` node's validated output flows to the next node exactly like a function node's return value does.

**The graph.** One new line, appended to Lesson 16's edges:

```python
loan_disbursement_workflow = Workflow(
    name="loan_disbursement_workflow",
    edges=[
        (START, calculate_deductions, calculate_net_payout, check_compliance_threshold),
        (check_compliance_threshold, {"needs_review": flag_for_review, "auto_clear": auto_disburse}),
        (flag_for_review, log_decision),
        (auto_disburse, log_decision),
        (log_decision, draft_notification, dispatch_notification),
    ],
)
```

**Running it.** This one needs a real, working model behind `get_model("primary")` to actually run, this lesson's sandbox has no live model access to demonstrate it end to end. The loan numbers stay exactly as deterministic as Lesson 16, base fee 1000, tax 180, net payout 48820 for a 50,000 loan. The notification text will not be deterministic, it is genuine model output, so do not expect to see the exact wording shown anywhere in this lesson reproduced on your own run. That variation is expected, not a bug, `output_schema` guarantees the shape of the reply, `subject` and `body` will always be there, it does not and should not guarantee the wording.

## Part 3: task mode

**What we are building.** A small, separate example, not wired into the loan graph. An agent that decides whether a loan in manual review qualifies for a short grace period, by calling a tool to check eligibility before deciding.

single_turn is one exchange. `task` mode is for a node that may need more than one, calling tools, seeing their results, calling more tools, for as many rounds as the model decides it needs. What ends a `task`-mode node is not a fixed number of rounds, it is an explicit signal. ADK attaches a tool called `finish_task` to every `task`-mode agent automatically, you never add it yourself. The model calls it when it is genuinely done, passing its final answer as that tool's arguments, shaped by the agent's `output_schema`. Whatever the model passes to `finish_task` becomes the node's output.

```python
def lookup_grace_period(loan_status: str) -> dict:
    if loan_status == "PENDING_MANUAL_REVIEW":
        return {"eligible": True, "max_days": 15}
    return {"eligible": False, "max_days": 0}


class GracePeriodDecision(BaseModel):
    eligible: bool
    extension_days: int


_grace_period_instruction = """You are a loan operations assistant.
You will receive a loan's status. Call `lookup_grace_period` with that
status to check eligibility, then decide the final extension in days.
Call `finish_task` once you have decided, do not just describe your
answer in text.
"""

grace_period_agent = Agent(
    name="grace_period_agent",
    model=get_model("primary"),
    description="Decides whether a loan qualifies for a grace period.",
    instruction=_grace_period_instruction,
    tools=[lookup_grace_period],
    mode="task",
    output_schema=GracePeriodDecision,
)
```

`mode="task"` is not optional to state here, this is the one place in this lesson where you have to ask for the behavior explicitly. `lookup_grace_period` is a plain function tool, nothing new about tool-calling itself, Lesson 3 already covered that. What is new is that the agent calling it is running as a graph node, and the graph waits for the whole multi-round exchange, tool call, tool result, then `finish_task`, before treating the node as complete.

```python
grace_period_workflow = Workflow(
    name="grace_period_workflow",
    edges=[(START, grace_period_agent)],
)
```

Running this needs a real model behind `get_model("primary")` too, same as Part 2. `lookup_grace_period`'s eligibility numbers are synthetic, not a real lending policy.

The deep version of this, an agent whose tools are themselves other agents, delegating work across a whole team rather than calling one plain function, is Lesson 16e's job, not this one. What you have here is task mode's core mechanic, working, on its own.

## Part 4: more than one terminal node

Every graph so far, in this lesson and in Lesson 16, converged back to a single node after branching. That is not a requirement. A graph can end in two genuinely different places, with nothing after either one.

```python
@node
async def route_request(ctx, node_input: str) -> str:
    ctx.route = node_input
    return node_input

@node
async def handle_as_a(node_input: str) -> str:
    return f"Path A handled: {node_input}"

@node
async def handle_as_b(node_input: str) -> str:
    return f"Path B handled: {node_input}"

two_terminal_workflow = Workflow(
    name="two_terminal_workflow",
    edges=[
        (START, route_request),
        (route_request, {"a": handle_as_a, "b": handle_as_b}),
    ],
)
```

No node follows `handle_as_a` or `handle_as_b`. Both are terminal. Run this with input `"a"` and `events[-1].output` is `'Path A handled: a'`. Run it with `"b"` and it is `'Path B handled: b'`. Whichever branch actually fired is the one `events[-1].output` reflects, correctly, every time. A graph with more than one ending is not a special case you need to guard against, `run_debug` already handles it exactly the way you would want it to.

## Part 5: Running the full lesson

```
adk2_tutorial/
└── agents/
    └── lesson16a_llm_nodes/
        ├── __init__.py
        ├── agent.py
        ├── main.py
        ├── task_mode_example.py
        └── multi_terminal_example.py
```

`agent.py` holds the full extended loan graph and exposes `root_agent`. `main.py` drives it, seeding `manual_review_limit` in state and running two loan amounts, the same pattern as Lesson 16's `main.py`. `task_mode_example.py` and `multi_terminal_example.py` are the two standalone examples from Parts 3 and 4, each runnable on its own.

From the project root:

```
uv run agents/lesson16a_llm_nodes/main.py
uv run agents/lesson16a_llm_nodes/task_mode_example.py
uv run agents/lesson16a_llm_nodes/multi_terminal_example.py
```

`multi_terminal_example.py` needs no model at all, it is pure function nodes, so it will run in this sandbox exactly as shown in Part 4. `main.py` and `task_mode_example.py` need `common/model_config.py` wired to a real, working model to actually reach a model and get a reply.

The same folder works with `adk web agents` too, `agent.py` exposes `root_agent` inside a proper subpackage, same discovery rule as every earlier lesson.

## What's next

This lesson put judgment inside a graph one node at a time. Lesson 16b turns to the graph's own shape: what makes a graph valid in the first place, and what happens when a `Workflow` is nested as a node inside another `Workflow`, a graph of graphs, along with `max_concurrency`, the control over how much of a graph is allowed to run at once.
