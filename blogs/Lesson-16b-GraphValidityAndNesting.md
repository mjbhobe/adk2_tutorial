# Lesson 16b: Graph Validity and Nesting

## Recap: Lesson 16a

Lesson 16a put an `Agent` inside a graph as a real node. No special wrapping needed, an `Agent` is built on the same foundation as `Workflow` itself, so it drops straight into an edges list. You saw `single_turn` mode, one exchange, the reply becomes the node's output, and along the way ran into a real gap between providers, `output_schema` alone does nothing on Claude, and a small placeholder tool is what switches on the fix. Then `task` mode showed the other shape, a node that can call tools across more than one round, deciding for itself when it is done.

## What this lesson covers

Two questions come up naturally once a graph grows past a handful of nodes. First, how do you know your graph is actually well-formed, before you ever run it, not after it fails halfway through. Second, can a graph be built out of smaller graphs, the way any large codebase is built out of smaller functions, rather than one enormous flat file of nodes. This lesson answers both, then adds a third piece, `max_concurrency`, which controls how much of a graph is allowed to run at the same time.

Nothing in this lesson needs a model. Every node here is a plain function, so everything you run will behave exactly as shown, no variation.

## Part 1: What makes a graph valid

`Workflow` checks your graph the moment you build it, before you ever call `run_debug`. A handful of rules decide whether that check passes:

- Every node needs a unique name. Two different nodes can't share one.
- `START` has to exist, and nothing can point into it. It is only ever a starting point.
- Every node has to be reachable from `START`. A node nothing leads to is just dead code sitting in the graph.
- You can't declare the same edge twice.
- A node can have at most one default, unconditional route out of it.
- A loop is only allowed if at least one edge in it is conditional, on `ctx.route`. A loop where every edge is unconditional would just spin forever, so the graph refuses to build one.

That last one is worth seeing directly. Two nodes pointing at each other with nothing to break the cycle:

```python
Workflow(name="wf", edges=[(START, a), (a, b), (b, a)])
```

fails immediately with:

```
Graph validation failed. Unconditional cycle detected: a -> b -> a.
Cycles must include at least one conditional (routed) edge to avoid
infinite loops.
```

A node that nothing points to:

```python
Workflow(name="wf", edges=[(START, a), (orphan, a)])
```

fails with:

```
Graph validation failed. The following nodes are unreachable from START: ['orphan']
```

Notice `orphan` has an outgoing edge, to `a`, but nothing ever leads into `orphan` itself, so it can never run. Same story for the same edge declared twice:

```python
Workflow(name="wf", edges=[(START, a), (a, b), (a, b)])
```

```
Graph validation failed. Duplicate edge found: from=a, to=b
```

None of these are exotic mistakes. They are exactly the kind of thing that creeps in once a graph has enough nodes that you stop holding the whole shape in your head at once, which is precisely when this checklist earns its keep.

## Part 2: Nesting

Consider the following. The loan disbursement graph from Lesson 16 works fine as one flat graph, but look closer at four of its nodes, the compliance check, its two branches, and the node they converge on. Together those four form a complete, self-contained decision: given a payout amount, decide auto-clear or manual review, and say which. If a later lesson needed that exact decision somewhere else, a different graph entirely, copying four nodes and their edges by hand is exactly the kind of duplication you would never accept in a function you were about to reuse.

A `Workflow` doesn't need to be reused as a copy. It can be reused as itself, dropped directly into another graph's edges, the same way any function node is. This lesson pulls those four nodes out into their own `Workflow`, `compliance_check_workflow`, and the outer graph uses it as a single node, no different in principle from `calculate_deductions`.

**Setup the folder structure.**

```
adk2_tutorial/
└── agents/
    └── lesson16b_graph_validity_nesting/
        ├── workflow.py
        ├── __init__.py
        └── main.py
```

**Code listings.**

`agents/lesson16b_graph_validity_nesting/workflow.py`

```python
"""
Lesson 16b: nested loan disbursement workflow

The compliance-check portion of the loan disbursement graph, pulled
out into its own Workflow, and reused as a single node inside the
outer graph.
"""

import json
from typing import Any

from google.adk.workflow import START, Workflow, node


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
    """The point both branches converge on, and the inner workflow's
    own terminal node.

    Args:
        node_input: The dict from either branch.

    Returns:
        The same dict, unchanged. Becomes the inner workflow's output,
        which becomes node_input for whatever follows it in the outer
        graph.
    """
    print(f"  [log_decision] final decision: {node_input}")
    return node_input


compliance_check_workflow = Workflow(
    name="compliance_check_workflow",
    edges=[
        (START, check_compliance_threshold, {"needs_review": flag_for_review, "auto_clear": auto_disburse}),
        (flag_for_review, log_decision),
        (auto_disburse, log_decision),
    ],
)

loan_disbursement_workflow = Workflow(
    name="loan_disbursement_workflow",
    edges=[(START, calculate_deductions, calculate_net_payout, compliance_check_workflow)],
)

root_agent = loan_disbursement_workflow
```

Read that last chain carefully: `(START, calculate_deductions, calculate_net_payout, compliance_check_workflow)`. The third element is not a node function, it is an entire `Workflow`, and it sits in that chain exactly like any node would. Whatever `calculate_net_payout` returns becomes `compliance_check_workflow`'s `node_input`, the same handoff every other pair of nodes in this series has used. And whatever `compliance_check_workflow` finishes on, `log_decision`'s return value, becomes the outer graph's result, since nothing follows it.

One more thing worth knowing: `ctx.state` is not sealed off inside the inner workflow. `manual_review_limit`, seeded on the session before the outer graph even starts, is exactly as visible to `check_compliance_threshold` running inside `compliance_check_workflow` as it would be to a node sitting directly in the outer graph. Nesting groups nodes together, it does not wall them off from each other.

Now the driver.

`agents/lesson16b_graph_validity_nesting/main.py`

```python
"""
Lesson 16b: driver for the nested loan disbursement workflow

Runs the outer workflow for two loan amounts, one that clears
automatically and one that trips manual review, exercising the
nested compliance_check_workflow both ways.
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
        user_id="lesson16b_user",
        session_id=session_id,
        state={"manual_review_limit": 1_000_000},
    )

    payload = json.dumps(
        {"loan_amount": loan_amount, "fee_percentage": 2.0, "gst_rate": 18.0}
    )

    events = await runner.run_debug(
        payload, quiet=True, session_id=session_id, user_id="lesson16b_user"
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
uv run agents/lesson16b_graph_validity_nesting/main.py
```

You will see this:

```
Run 1: a loan that clears automatically
  [calculate_deductions] base_fee=1000.0, tax=180.0, total_deductions=1180.0
  [calculate_net_payout] {'net_disbursement': 48820.0, 'status': 'READY_FOR_TRANSFER'}
  [check_compliance_threshold] net_disbursement=48820.0, manual_review_limit=1000000.0
  [log_decision] final decision: {'net_disbursement': 48820.0, 'status': 'AUTO_DISBURSED'}
loan_amount=50000 -> {'net_disbursement': 48820.0, 'status': 'AUTO_DISBURSED'}

Run 2: a loan that trips manual review
  [calculate_deductions] base_fee=100000.0, tax=18000.0, total_deductions=118000.0
  [calculate_net_payout] {'net_disbursement': 4882000.0, 'status': 'READY_FOR_TRANSFER'}
  [check_compliance_threshold] net_disbursement=4882000.0, manual_review_limit=1000000.0
  [log_decision] final decision: {'net_disbursement': 4882000.0, 'status': 'PENDING_MANUAL_REVIEW'}
loan_amount=5000000 -> {'net_disbursement': 4882000.0, 'status': 'PENDING_MANUAL_REVIEW'}
```

Same numbers as Lesson 16, same two outcomes. What changed is entirely structural, four nodes now live inside their own `Workflow` instead of sitting flat in the outer one, and the outer graph doesn't know or care about that difference.

## Part 3: max_concurrency

Consider the following. A new loan application comes in, and before anything else happens, three separate checks need to run against it, a credit check, a fraud check, and an income verification. None of these three depends on the other two, credit history doesn't need to wait on a fraud flag. Running them one after another would just be wasted time, each one is its own lookup against its own system, so there is no reason not to run all three at once.

A `Workflow` can fan a single trigger out to more than one node at the same time, and it does exactly that here. But "at the same time" raises its own question: what if a graph fans out to twenty things at once, not three? Real external systems have rate limits, and a graph that fires everything simultaneously, with no restraint, is not necessarily faster, it can just as easily get every one of those calls throttled or rejected. `max_concurrency` is the setting that controls this, a cap on how many graph-triggered nodes are allowed to run at the same moment. Leave it unset, and there is no cap. Set it to `1`, and the graph runs those same three nodes one at a time, in whichever order they happen to be picked up.

**Setup the folder structure.**

```
adk2_tutorial/
└── agents/
    └── lesson16b_graph_validity_nesting/
        └── max_concurrency_example.py
```

**Code listing.**

`agents/lesson16b_graph_validity_nesting/max_concurrency_example.py`

```python
"""
Lesson 16b: max_concurrency example

Three independent checks on a new loan application, fanned out to run
at once, then converged. Runs the same graph twice, once unlimited
and once capped at max_concurrency=1, so the timing difference is
visible directly.

Every check here just sleeps to stand in for a slow external lookup,
credit bureau, fraud database, income verification service. None of
it is real, the timing behavior is what matters.
"""

import asyncio
import json
import time

from google.adk.workflow import START, Workflow, node, JoinNode
from google.adk.runners import InMemoryRunner


@node
async def intake(ctx, node_input: str) -> dict:
    """Parses the incoming loan application.

    Args:
        ctx: The node's execution context. Unused here.
        node_input: A JSON string with the applicant id.

    Returns:
        The parsed application dict.
    """
    return json.loads(node_input)


@node
async def credit_check(node_input: dict) -> dict:
    """Simulates a credit bureau lookup.

    Args:
        node_input: The application dict.

    Returns:
        A dict with a synthetic credit_score.
    """
    print("  [credit_check] started")
    await asyncio.sleep(0.5)
    print("  [credit_check] finished")
    return {"credit_score": 720}


@node
async def fraud_check(node_input: dict) -> dict:
    """Simulates a fraud database lookup.

    Args:
        node_input: The application dict.

    Returns:
        A dict with a synthetic fraud_flag.
    """
    print("  [fraud_check] started")
    await asyncio.sleep(0.5)
    print("  [fraud_check] finished")
    return {"fraud_flag": False}


@node
async def income_check(node_input: dict) -> dict:
    """Simulates an income verification lookup.

    Args:
        node_input: The application dict.

    Returns:
        A dict with a synthetic income_verified flag.
    """
    print("  [income_check] started")
    await asyncio.sleep(0.5)
    print("  [income_check] finished")
    return {"income_verified": True}


join_checks = JoinNode(name="join_checks")


def build_intake_workflow(max_concurrency: int | None = None) -> Workflow:
    """Builds the intake workflow, optionally capping parallel nodes.

    Args:
        max_concurrency: Maximum number of graph-scheduled nodes
            allowed to run at once. None means unlimited.

    Returns:
        A fresh Workflow instance.
    """
    return Workflow(
        name="intake_workflow",
        edges=[(START, intake, (credit_check, fraud_check, income_check), join_checks)],
        max_concurrency=max_concurrency,
    )


async def run(workflow: Workflow, label: str) -> None:
    """Runs the given workflow once and prints the elapsed time.

    Args:
        workflow: The Workflow to run.
        label: A short label identifying this run in the printed output.
    """
    runner = InMemoryRunner(agent=workflow)
    start = time.time()
    events = await runner.run_debug('{"applicant_id": "A123"}', quiet=True)
    elapsed = time.time() - start
    print(f"{label}: {elapsed:.2f}s total -> {events[-1].output}\n")


async def main() -> None:
    """Runs the intake workflow unlimited, then capped at 1."""
    await run(build_intake_workflow(), "No max_concurrency (default, unlimited)")
    await run(build_intake_workflow(max_concurrency=1), "max_concurrency=1")


if __name__ == "__main__":
    asyncio.run(main())
```

Two new things in this file. `(credit_check, fraud_check, income_check)`, a plain tuple sitting where a single node would normally go, is how you fan a trigger out to more than one node at once. And `JoinNode`, `join_checks`, is what the three branches converge on afterward. A `Workflow` will not let a run finish with more than one node's output competing to be the final result, so once you fan out, something has to bring the branches back together before the graph can end. `JoinNode` does exactly that and nothing else, it waits for every branch feeding into it and hands their combined results on as one dict, keyed by node name. What each branch actually does with real business logic, and picking which pieces of a real fan-out to converge versus leave separate, is Lesson 16i's job. Here, `JoinNode` is just the minimum plumbing needed to let this graph finish cleanly.

**Run the code.**

Start a new terminal and from the project root folder (`adk2_tutorial`) run the following commands:

```bash
# activate your local environment
source .venv/bin/activate
# run the program
uv run agents/lesson16b_graph_validity_nesting/max_concurrency_example.py
```

You will see this:

```
  [credit_check] started
  [fraud_check] started
  [income_check] started
  [credit_check] finished
  [fraud_check] finished
  [income_check] finished
No max_concurrency (default, unlimited): 0.52s total -> {'credit_check': {'credit_score': 720}, 'income_check': {'income_verified': True}, 'fraud_check': {'fraud_flag': False}}

  [credit_check] started
  [credit_check] finished
  [fraud_check] started
  [fraud_check] finished
  [income_check] started
  [income_check] finished
max_concurrency=1: 1.51s total -> {'credit_check': {'credit_score': 720}, 'income_check': {'income_verified': True}, 'fraud_check': {'fraud_flag': False}}
```

Look at the "started" and "finished" lines, not just the final numbers. In the first run, all three checks start before any of them finish, genuinely running at once, and the whole thing takes roughly as long as one check alone, about half a second. In the second run, each check starts only after the previous one has fully finished, three checks back to back, and the total is roughly three times as long. Same graph, same three checks, the only thing that changed between the two runs is one number.

## What's next

This lesson gave you a checklist for a graph's own correctness, unique names, a clean start, no dead nodes, no runaway loops, and two ways to control a graph's shape once it grows, nesting a `Workflow` inside another to group related nodes together, and `max_concurrency` to keep a fan-out from running wild.

Lesson 16c turns to graphs whose shape isn't fixed in advance at all, deciding the next node to run at runtime rather than laying out every path upfront, and how to do that safely without accidentally repeating work if a node reruns.
