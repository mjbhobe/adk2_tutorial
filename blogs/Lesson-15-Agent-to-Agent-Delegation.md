# Lesson 15: Agent-to-Agent Delegation (A2A)

`AgentTool` (Lesson 11d) reaches another agent, but one living in your own process, your own code. MCP (Lesson 14) reaches outside your process, but _only_ for tools and data. A2A (Agent-to-Agent) is the remaining case: reaching an entire other *agent*, one that lives in a genuinely separate process, possibly owned by a different team, possibly built on a completely different framework, over an open, cross-vendor protocol rather than an import or a direct function call.

## What A2A actually is

A2A defines a client-server relationship between agents, the same shape MCP defines between an agent and a tool server, but one level up. An A2A **server** exposes an agent's capabilities over the protocol. An A2A **client** connects to it and can send that agent tasks, and get results back, without needing to know or care what framework, or what language, the server side actually runs on.

The distinction from MCP is worth stating plainly, since the two protocols solve adjacent but different problems: MCP connects an agent to *tools and data it doesn't have*. A2A connects an agent to *another agent's own reasoning*, a full LLM-driven participant on the other end, not a function that returns a value.

![A2A Delegation](images/A2A_Delegation.png)

So how does a client agent figure out what a remote agent is actually capable of, before it ever sends it a task?

## Consider this agent

To understand the A2A mechanics, let's consider the `risk_specialist_agent`, which we built in Lesson `13a`:

```python
from google.adk.agents import Agent

from common.model_config import get_model

from .tools import calculate_risk_score

instruction = """You are a loan risk specialist. Given an applicant's
credit_score, annual_income, loan_amount, tenure_months, and
has_defaults, call `calculate_risk_score` with those five values and
report the risk_score, risk_band, and emi_to_income_ratio back.

Always call the tool. Never estimate the score yourself.
"""

risk_specialist_agent = Agent(
    name="risk_specialist_agent",
    model=get_model("primary"),
    description="Assesses loan risk given credit and applicant details, and returns a risk score and band.",
    instruction=instruction,
    tools=[calculate_risk_score],
)
```

There is nothing new here; by now you should be able to fully understand the above definition. We have used a simple agent definition, but this could very well be a `SequentialAgent`, a `ParallelAgent`, a `LoopAgent` or any other complex workflow by combining these agents - from the consumer's PoV, we shouldn't really _care_ what type of agent this is. 

An agent that can be "consumed" over the A2A protocol needs to be _served_ on an API endpoint, so other agents can connect to it and "consume" the service(s) it offers. But before we start serving our agent over A2A, we'll need to install two more libraries into our local `uv` managed environment. `google-adk[a2a]` and `sse_starlette`. `google-adk[a2a]` gives you the `to_a2a()` and the `RemoteA2aAgent` features, and `sse_starlette` is a separate dependency the `a2a` SDK's server routing needs to serve an agent.

Add these libraries to your local `uv` environment by running the following command the root `adk2_tutorial` folder in a new terminal.

```bash
source .venv/bin/activate
uv add "google-adk[a2a]==2.5.0" sse_starlette
```

As with other ADK libraries, we pin this one to version 2.5.0 too.

## Serving an agent over A2A

To serve an Agent as an A2A server, create a new Python file with the following code:

```python
from google.adk.a2a.utils.agent_to_a2a import to_a2a
import uvicorn

# import our agent
from risk_specialist.agent import risk_specialist_agent

app = to_a2a(
  risk_specialist_agent,  # publish which agent?
  host="localhost",       # on which web-address?
  port=8001               # on which port?
)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
```

That's it! The `to_a2a()` function takes the agent and wraps it into a full A2A server, returning a Starlette app (the framework FastAPI itself is built on). We can access this agent at `https://127.0.0.1:8001`.

The `uvicorn.run(...)` at the bottom is what actually starts the server, the same pattern every FastAPI server in this series has used since Lesson 9. Save the code above as its own file (say `risk_service.py`) and run it directly, `uv run risk_service.py`, and it exposes two things automatically: the actual task-execution endpoint, and an Agent Card discovery endpoint. Nothing about `risk_specialist_agent` itself needed to change to become servable this way.

So how does a client agent figure out what this now-running server can actually do, before it ever sends it a task?

## The Agent Card

An A2A server advertises what it can do through an **Agent Card**, a JSON document served at a standard, discoverable location, `/.well-known/agent-card.json`. It's A2A's equivalent of an MCP server's tool list, the thing a client reads before deciding to engage.

### Where this file actually lives

Despite how it looks, `/.well-known/agent-card.json` is **not a file path on your computer**. It's a URL path, the last part of an address like `http://localhost:8001/.well-known/agent-card.json`. The `/.well-known/` prefix is a real, standard convention (RFC 8615) for exactly this purpose, service metadata living at a predictable address, nothing to do with your project's folder structure.

More importantly: in the normal flow, **you never create this file at all**. The `to_a2a()` call above already built one, in memory, directly from `risk_specialist_agent` by extracting its name, description, and skills are extracted automatically, and it started serving that card as a live response the moment the server started. Nothing was saved anywhere.

### The exact card `to_a2a()` generates for `risk_specialist_agent`

```json
{
  "name": "risk_specialist_agent",
  "description": "Assesses loan risk given credit and applicant details, and returns a risk score and band.",
  "url": "http://localhost:8001/",
  "version": "1.0.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": [
    {
      "id": "calculate_risk_score",
      "name": "calculate_risk_score",
      "description": "Assesses loan risk given credit and applicant details, and returns a risk score and band."
    }
  ]
}
```

Notice `name`, `description`, and `url` come straight from the agent object and the `host/port` given to `to_a2a()`, nothing here needed to be written by hand.

> **NOTE:** `skills` here, the field in the middle of that JSON, is A2A's own formal term for the discrete capabilities a remote agent advertises. It has nothing to do with ADK's Skills system from Lesson 13, same word, two unrelated concepts, defined by two different specifications. When you see "skills" in an Agent Card, it means "things this remote agent can do," not `SKILL.md` files.

### The fields, and which ones are actually required

| Field | Holds | Required? |
|---|---|---|
| `name` | Human-readable agent name | Yes |
| `description` | What the agent does | Yes |
| `url` | The endpoint clients should call to interact with it | Yes |
| `version` | The agent's own version string | Yes |
| `capabilities` | Whether it supports streaming, push notifications, state history | Yes |
| `default_input_modes` | MIME types the agent accepts by default, e.g. `text/plain` | Yes |
| `default_output_modes` | MIME types the agent returns by default | Yes |
| `skills` | The list of distinct capabilities this agent advertises | Yes |
| `provider` | Who runs this agent | No |
| `documentation_url` | Link to human-readable docs | No |
| `icon_url` | Link to an icon | No |
| `security_schemes` / `security` | What authentication this agent expects | No |
| `preferred_transport` | `JSONRPC`, `GRPC`, or `HTTP+JSON`, defaults to `JSONRPC` | No |
| `protocol_version` | Which A2A protocol version this agent supports, defaults to `0.3.0` | No |

> 📌 **NOTE** It's worth being _precise_ about what "optional" means here, since it's not the same for every row. 
>
>`preferred_transport` and `protocol_version` have real defaults built into the schema, `JSONRPC` and `0.3.0`, so the auto-generated card always includes a sensible value for both, no customization needed. 
>
> However there is nothing in the `Agent` definition to infer values for any of the fillowing fields: `provider`, `documentation_url`, `icon_url`, and `security_schemes/security`, so the auto-generated card leaves them out entirely.


### When you'd actually want a custom card instead

Getting any of those four fields into the card means supplying a hand-written one instead. The auto-generated card only knows what it can read off the agent object itself, it has no way to know who runs this service, or where to point people for documentation, information that genuinely isn't part of an ADK `Agent`. `to_a2a()`'s `agent_card` parameter accepts a path to a hand-written JSON file for exactly this case:

```python
app = to_a2a(
    risk_specialist_agent,
    host="localhost",
    port=8001,
    agent_card="risk_specialist_agent_card.json",
)
```

That file would carry everything the auto-generated version has, plus fields nothing could infer automatically, `provider`, for instance:

```json
{
  "provider": {
    "organization": "Your Company Name",
    "url": "https://yourcompany.example"
  }
}
```

Reach for this when the auto-generated card is missing something you specifically want a consumer to see, not as a routine step, the automatic version covers the common case correctly on its own.

## Consuming a remote agent

Now imagine a second process, a loan orchestrator, that needs a risk assessment for an application it's handling. The agent that can actually do that, `risk_specialist_agent`, isn't running inside this process at all anymore, it's the server just stood up above. Here's how the orchestrator reaches it.

```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

remote_agent = RemoteA2aAgent(
    name="risk_assessment_agent",
    agent_card="http://localhost:8001/.well-known/agent-card.json",
)
```

`RemoteA2aAgent` accepts the card three different ways:

```python
# 1. A URL, the form you'll use most often, pointing at a running server's discovery endpoint
remote_agent = RemoteA2aAgent(
    name="risk_assessment_agent",
    agent_card="http://localhost:8001/.well-known/agent-card.json",
)

# 2. A local file path to a saved card
remote_agent = RemoteA2aAgent(
    name="risk_assessment_agent",
    agent_card="risk_specialist_agent_card.json",
)

# 3. A direct AgentCard object, when you already have one loaded or built in code
remote_agent = RemoteA2aAgent(
    name="risk_assessment_agent",
    agent_card=my_agent_card,  # an AgentCard instance
)
```

The URL form is what you'll use most in practice, the other two matter when you're testing against a saved card, or building one programmatically rather than fetching it live.

The detail that matters most: `RemoteA2aAgent` is itself a `BaseAgent`. Everything Lesson `11d` already taught applies to it completely unchanged, wrap it in `AgentTool` for a calling agent's model to decide when to delegate, or use it directly as a sub-agent in a `SequentialAgent`. The network boundary disappears once you have one, it behaves like any other agent from that point on.

```python
from google.adk.tools.agent_tool import AgentTool

orchestrator = Agent(
    name="loan_orchestrator",
    model=get_model("primary"),
    tools=[AgentTool(agent=remote_agent)],
)
```

But `AgentTool` isn't the only option, it's the one for when a model needs to decide whether to delegate, the same routing judgment Lesson `11d` covered. If the remote agent's turn is always part of a fixed sequence instead, no decision needed, it slots directly into a `SequentialAgent` as an ordinary sub-agent, no wrapper at all:

```python
from google.adk.agents import SequentialAgent

loan_pipeline = SequentialAgent(
    name="loan_pipeline",
    sub_agents=[credit_agent, remote_agent, decision_agent],
)
```

Same `remote_agent`, two different roles, chosen the same way you'd choose between them for any local agent, AgentTool for a model's own judgment call, a plain sub-agent for a step that always runs.

## The task lifecycle

Every request an A2A client sends becomes a task on the server side, and that task moves through a real, formal state machine, more nuanced than anything else in this series has needed. Eight states, each meaning something specific:

- **`SUBMITTED`**: the task has been received and accepted, but work hasn't started yet. This is the very first state, before the server has actually begun processing anything.
- **`WORKING`**: the agent is actively processing the task. For anything that takes real time, this is where a task sits while the remote agent is reasoning, calling its own tools, or waiting on something of its own.
- **`COMPLETED`**: the task finished successfully, and a result is available to read. A terminal state, nothing more happens to this task after this.
- **`FAILED`**: something went wrong on the server side, an error the agent couldn't recover from. Also terminal, and worth distinguishing from `REJECTED` below, this means the task was accepted and attempted, then failed partway through.
- **`CANCELED`**: the task was stopped before completing, either the client asked to cancel it, or the server had a reason to stop. Terminal, and distinct from `FAILED`, nothing necessarily went wrong, the task was just called off.
- **`REJECTED`**: the server declined to even start the task, before ever entering `WORKING`. This is the "I won't attempt this at all" response, an invalid request, something outside the agent's declared skills, or a request the server has a policy reason to refuse outright.
- **`INPUT_REQUIRED`**: the task paused mid-flight because the remote agent needs more information from the caller before it can continue. This is the protocol-level version of exactly the problem Lesson 12 solved by hand: a remote agent can genuinely pause, signal what it needs, and resume once that input arrives, the same shape as `ResumabilityConfig`'s pause-and-resume, except here it's native to the protocol rather than something built manually with a `LongRunningFunctionTool`. Not terminal, the task picks back up once the caller responds.
- **`AUTH_REQUIRED`**: the same pausing behavior as `INPUT_REQUIRED`, specifically for the case where the remote agent needs the caller to complete an authorization step before it can continue. Also not terminal.

Two states, `SUBMITTED` and `WORKING`, mark a task still in progress. Three, `COMPLETED`, `FAILED`, and `CANCELED`, are terminal, nothing more happens to the task once it reaches one of them. `REJECTED` is a special terminal case, one that never really started at all. And two, `INPUT_REQUIRED` and `AUTH_REQUIRED`, are genuinely paused, not finished, not failed, just waiting.

## A2A, MCP, `AgentTool`, and Skills, the full picture

Four lessons now have covered a way to reach beyond an agent's own fixed instruction, and this is the natural point to see all four side by side.

| | Reaches | Same process? | What's on the other end |
|---|---|---|---|
| Skills (13) | Knowledge and procedure | Yes | Instructions, optionally a script |
| `AgentTool` (11d) | A whole other agent | Yes | Another agent, your own code |
| MCP (14) | Tools and data | No | A tool server, not a reasoning agent |
| A2A (15) | A whole other agent | No | Another agent, possibly a different framework entirely |

A2A is `AgentTool`'s cross-process counterpart in exactly the way MCP is a plain function tool's cross-process counterpart. Same underlying idea, reach something that isn't yours, twice over, once for "another agent" and once for "a tool," each with an in-process and an out-of-process version.

## Real-world considerations

**Timeouts.** `RemoteA2aAgent` defaults to a 600-second timeout, generous, but a real number, not infinite. A remote agent that's slow, overloaded, or genuinely stuck will eventually cause the call to fail rather than hang forever, worth knowing before you're debugging why a request took ten minutes to return an error.

**An unreachable remote agent** fails the same way any HTTP client failure would, connection refused, DNS failure, timeout, nothing A2A-specific to it. Your own agent's error handling needs to account for the remote service simply not being there, the same discipline any distributed system needs.

**Auth for a remote agent** parallels `McpToolset`'s story from Lesson 14: the Agent Card's own `security_schemes` and `security_requirements` fields describe what a server expects, and `RemoteA2aAgent`'s constructor accepts a custom `httpx_client` (or, in the newer path, an `a2a_client_factory`) for supplying credentials, a bearer token, an API key, whatever the specific server requires, the same shape of problem, solved the same general way.

## In this lesson

You learned what A2A actually adds beyond `AgentTool` and MCP, the ability to reach a genuinely separate agent, in a separate process, described through a standard Agent Card rather than imported code. You saw both sides, `to_a2a()` for serving, `RemoteA2aAgent` for consuming, and the one detail that ties it back to everything already built: `RemoteA2aAgent` being a `BaseAgent` means nothing about orchestrating it is new, only what's actually on the other end of the connection is. You saw A2A's own `skills` field disambiguated from ADK's Skills system, and its task lifecycle, especially `INPUT_REQUIRED`, connected directly to the HITL problem Lesson 12 solved manually.

## In the next lesson

`15a` builds this for real: a loan orchestrator in one process, delegating risk assessment to a separately-run risk service in another, reusing the risk-scoring formula from 11a, 12, and 13a so the lesson's focus stays on the network boundary and Agent Card discovery, not a new domain formula.
