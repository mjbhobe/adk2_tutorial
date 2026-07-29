# Lesson 7: Callbacks — Hooks into the Heart of Every Turn

Lessons 6a and 6b gave you two ways to touch session state: pre-seeding it from `main.py` before the conversation starts, and writing to it from inside a tool during a turn. Both of those are tied to specific, explicit moments, the application choosing to pre-load something, or the model choosing to call a tool. But some behaviour in a real agent system doesn't belong to any one of those moments. You might want to log every single model call, regardless of which tool it ends up calling. You might want to reject a request before it ever reaches the model, if it fails a compliance check. You might want to scan every tool result for sensitive data before the model reads it. None of those fit neatly inside a tool or a session pre-load. That's what _callbacks_ exist for.

This is a theory-only lesson. No new code to run. The goal is to give you a clear mental model of the six callback types, what fires when, what each one can do, and when you should reach for each one, before Lesson 7a builds a real application that puts all of them to work together.

## What a callback actually is

A callback in ADK is a plain Python function, `async` or sync, that ADK invokes automatically at a specific point in the processing of a turn. You write it yourself, register it on an agent by name (like `before_agent_callback=my_function`), and ADK calls it for you at the right moment, every single turn, without you having to trigger it manually.

The function receives a context object that gives it access to the current session, its state, and other details about what's happening right now. Depending on which callback point you're at, the context might also carry the model's request, the model's response, or a tool's result, things you can inspect, modify, or replace. And depending on what you return from the callback, you can either let the normal processing continue (return `None`) or short-circuit it entirely (return an actual value, which ADK will use as the result for that step, skipping whatever would have happened next).

That last point, the ability to short-circuit, is what gives callbacks their real power. A before-model callback that returns a response object stops the model call from happening at all and uses your response instead. A before-tool callback that returns a dict stops the tool from executing and uses your dict as the result. This is how you build guardrails, caching, rate limiting, and mock responses, all without touching the agent's core logic.

## The six callback points

Every turn of a conversation passes through up to six potential callback interception points, in this order:

```
Before Agent
    └── Before Model
            └── [Model call]
        After Model
            └── Before Tool (once per tool call, if any)
                    └── [Tool execution]
                After Tool (once per tool call, if any)
            (Model called again if tools were used...)
After Agent
```

This image illustrates the process more clearly

![ADK Callbacks](images/ADK%20Callbacks.png)

Tools may fire multiple times in a single turn if the model decides to call several tools before giving its final answer, so `before_tool_callback` and `after_tool_callback` can each fire more than once per turn. Everything else fires once per turn.

Let's look at each one precisely.

## Before Agent callback

**When it fires:** at the very start of every turn, before anything else happens, before the model is called, before any tool runs.

**Signature:**
```python
async def my_callback(callback_context: CallbackContext) -> Optional[types.Content]:
```

**What it can do:** read and write `callback_context.state`, inspect `callback_context.user_content` (the incoming message), and access `callback_context.session`, `user_id`, `agent_name`.

**What returning a value means:** if you return a `types.Content` object, ADK uses that as the agent's final response for this turn and skips everything else: no model call, no tools. If you return `None`, the turn proceeds normally.

**What to use it for:**
- **Access control and compliance pre-checks.** If a customer's tier doesn't allow a certain operation, reject it here with a friendly response, before the model ever sees the message. This is cheaper than letting the model process a request you're going to block anyway.
- **Session bookkeeping that applies every turn.** Incrementing a turn counter, logging a conversation event, setting a timestamp for the start of this turn. Things that should happen regardless of what the customer said.
- **Input validation or redirection.** Detect that a message is clearly off-topic and return a standard response directly, rather than burning model tokens on it.

**What not to do here:** don't make decisions based on what the model said or what tools returned, since neither has happened yet. Don't do anything computationally heavy that should only happen when a tool actually fires.

## Before Model callback

**When it fires:** immediately before each call to the LLM. In a turn where the model calls several tools and then produces a final answer, this fires once before the very first model call only; subsequent model calls (after tool results come back) are not intercepted again by this callback in the current implementation.

**Signature:**
```python
async def my_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
```

**What it can do:** everything `before_agent_callback` can do, plus it receives the `LlmRequest` object directly. `LlmRequest` is the fully assembled package about to be sent to the model: the system prompt, the conversation history, the tool schemas, any media. You can read it and mutate it in place, adding context, modifying the system prompt, injecting additional instructions without touching the agent's stored instruction string.

**What returning a value means:** if you return an `LlmResponse`, that response is used as the model's output for this turn and the actual model call is skipped entirely. If you return `None`, the (possibly mutated) request is sent to the model as normal.

**What to use it for:**
- **Dynamic context injection.** Fetch a live interest rate, a customer's account balance, or a real-time market price and inject it directly into the prompt right before the model call, so the model always has up-to-date information without that data needing to be baked into the agent's static instruction.
- **Prompt guards.** Scan the assembled request for terms or patterns your compliance team has flagged, and either block the call or add a compliance reminder before it goes out.
- **Response caching.** Check a cache for a prior response to this exact request; if you have one, return it directly and skip the model call entirely, saving both latency and cost.
- **Model call logging.** Log every request for audit purposes, since this is the only callback that gives you the complete, assembled request before it leaves your system.

**What not to do here:** avoid making the `LlmRequest` mutation so complex that it's hard to reason about what the model is actually receiving. Mutations here are invisible to the agent definition code, which can make debugging confusing if overused.

## After Model callback

**When it fires:** immediately after the LLM responds, before ADK processes that response (before any tool calls the model requested are executed).

**Signature:**
```python
async def my_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
```

**What it can do:** everything the before callbacks can do, plus it receives the actual `LlmResponse`. You can inspect the model's text output, the tool calls it's requesting, or any other content in the response.

**What returning a value means:** if you return an `LlmResponse`, that replaces the model's actual response for everything that comes after (tool execution, final answer). If you return `None`, the real response proceeds.

**What to use it for:**
- **Content filtering.** Scan the model's output for prohibited terms, investment advice language, personally identifiable information, or other content your compliance rules prohibit. You can modify or replace the response here before any user or downstream system sees it.
- **Response enrichment.** Add standard disclaimers, legal notices, or structured metadata to the model's output without baking that text permanently into the instruction string.
- **Output monitoring.** Log the model's raw response for quality evaluation or fine-tuning data collection, before any subsequent processing changes it.

**What not to do here:** don't make assumptions about what the model was responding to by re-reading the user's message from state; use `callback_context.user_content` instead, since it's always the current turn's input. And be careful about replacing responses entirely here; doing it too aggressively can break tool-calling flows, since the model's tool call requests live inside the `LlmResponse` object.

## Before Tool callback

**When it fires:** immediately before each individual tool execution. If the model requested three tool calls in one turn, this fires three times, once before each one.

**Signature:**
```python
async def my_callback(tool: BaseTool, args: dict, tool_context: ToolContext) -> Optional[dict]:
```

**What it can do:** inspect the tool being called (`tool.name`), the exact arguments ADK is about to pass to it (`args`), and read/write session state through `tool_context.state`.

**What returning a value means:** if you return a dict, ADK uses that as the tool's result and skips the actual tool execution. If you return `None`, the tool runs as normal.

**What to use it for:**
- **Argument validation.** Check that the arguments the model is passing to a tool make sense before the tool runs. If a loan amount is negative or a ticker symbol is blank, reject it here with a structured error dict rather than letting it propagate into the tool's own error handling.
- **Tool-call logging and auditing.** Record every tool invocation with its arguments, essential for a regulated environment where you need to explain exactly what your agent did and why.
- **Mocking for testing.** In a test environment, intercept calls to external tools (an API, a database) and return canned responses instead. This keeps tests fast and deterministic.
- **Rate limiting.** Check a call counter in state and return an error dict if a particular tool is being called too many times in one turn, preventing runaway tool-calling loops.

**What not to do here:** don't perform the tool's actual work yourself and return the result unless you're deliberately mocking. And don't use this callback to change what tool gets called; by the time this fires, the routing decision has already been made.

## After Tool callback

**When it fires:** immediately after each tool execution completes, before the result is returned to the model. Like `before_tool_callback`, this fires once per tool call, potentially multiple times per turn.

**Signature:**
```python
async def my_callback(tool: BaseTool, args: dict, tool_context: ToolContext, tool_response: dict) -> Optional[dict]:
```

**What it can do:** everything `before_tool_callback` can do, plus it receives the actual `tool_response`, the dict your tool returned. You can inspect or modify it.

**What returning a value means:** if you return a dict, that replaces the tool's actual response as what the model sees. If you return `None`, the real response is passed to the model.

**What to use it for:**
- **Sensitive data redaction.** Scrub PII or account numbers from a tool's response before the model reads it and potentially echoes it back to the user in its reply.
- **Result validation.** Check that a tool's return value makes sense before the model acts on it. A stock price tool that returns a negative number, or a credit score tool that returns a value outside the expected range, can be caught and replaced with an error signal here.
- **Result enrichment.** Add metadata, provenance information, or a timestamp to a tool's raw result before the model sees it, so the model can reference it accurately in its answer.
- **Error normalisation.** Convert tool-specific exception formats into a consistent structured error shape your model has been trained to handle gracefully.

## After Agent callback

**When it fires:** at the very end of every turn, after the model has produced its final answer, after all tools have run, after everything else has completed.

**Signature:**
```python
async def my_callback(callback_context: CallbackContext) -> Optional[types.Content]:
```

**What it can do:** the same as `before_agent_callback`: read/write state, access session and user details. Crucially, it also has access to `callback_context.add_session_to_memory()`, which is how you trigger long-term memory saving.

**What returning a value means:** if you return `types.Content`, that replaces the agent's final response as what gets surfaced to the caller. If you return `None`, the real final response is used.

**What to use it for:**
- **Saving to long-term memory.** This is the primary use of `after_agent_callback` in this series. Calling `await callback_context.add_session_to_memory()` here ensures that whatever was said in this turn gets stored for potential recall in future sessions, covering Lesson 8 (Memory) naturally.
- **Turn-completion logging.** Record that a turn completed, how long it took, whether it used tools, and what the final answer was.
- **Post-response state updates.** Write any bookkeeping that should happen at turn completion, like updating a "last active" timestamp or marking a workflow step as done.
- **Response transformation for the caller.** If the raw agent response needs to be reformatted before it reaches your application layer (say, wrapping it in a structured JSON envelope), this is the right place.

## The CallbackContext object

Every callback except the tool callbacks receives a `CallbackContext`. This is worth understanding as its own object, since it's your window into the running conversation from inside any callback.

The most important things it exposes:

| Property / Method | What it gives you |
|---|---|
| `callback_context.state` | Read-write access to the current session's state dictionary |
| `callback_context.session` | The full `Session` object for this conversation |
| `callback_context.user_id` | The user identifier for this conversation |
| `callback_context.agent_name` | The name of the agent currently running |
| `callback_context.user_content` | The user's message that started this turn |
| `callback_context.invocation_id` | A unique ID for this specific turn, useful for logging |
| `callback_context.add_session_to_memory()` | Saves the current session to long-term memory (async) |

The tool callbacks receive a `ToolContext` instead, which exposes the same `state`, `session`, and `user_id`, and adds tool-specific capabilities like `save_artifact()` and `search_memory()`.

## One important constraint: the parameter name is enforced

Every callback function in ADK must name its first parameter exactly `callback_context` (for agent and model callbacks) or follow the exact positional signature for tool callbacks. This is not a convention, ADK inspects the function signature and raises an error if the name doesn't match. So while you can name your callback function anything, the parameter names inside it are fixed.

## Sync versus async

All six callback types support both synchronous and asynchronous implementations. If your callback doesn't need to await anything (it's just reading state and doing an in-memory check), a plain `def` works fine. If it needs to call an API, query a database, or use any ADK async method like `add_session_to_memory()`, it must be `async def`. Either form is accepted wherever a callback can be registered.

## A practical guide: which callback for which job

| Job | Right callback |
|---|---|
| Block a request before the model sees it | `before_agent_callback` |
| Increment a turn counter or session-level bookkeeper | `before_agent_callback` |
| Inject live data into the prompt | `before_model_callback` |
| Scan the model's output for prohibited content | `after_model_callback` |
| Log every model request for audit | `before_model_callback` |
| Validate tool arguments before they run | `before_tool_callback` |
| Log every tool call for a regulated audit trail | `before_tool_callback` |
| Redact PII from a tool's result | `after_tool_callback` |
| Save the conversation to long-term memory | `after_agent_callback` |
| Reformat the final response for the calling system | `after_agent_callback` |

## In the next lesson

Lesson 7a puts everything in this lesson to work in one cohesive application: a wealth management advisory agent that uses all six callback types simultaneously, each one doing a distinct, realistic job, so you can see how they work together in practice rather than in isolation.
