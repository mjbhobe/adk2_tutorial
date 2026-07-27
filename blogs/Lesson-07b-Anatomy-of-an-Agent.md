# Lesson 7b: The Anatomy of an ADK Agent

Six lessons plus 7a have each handed you one piece of ADK in isolation: a model here, a tool there, a session, a memory service, a way to serve it all behind an API. That's the right way to learn a framework, but it leaves a gap: you've never seen all of it sitting together in one running system, with each piece labeled and in its place. This lesson closes that gap. No new code, no new agent to build, just a deliberate, detailed pass over everything you've assembled so far, so it clicks into a single picture before we start making that picture more complicated in Lesson 8.

Here's that picture:

![Anatomy of an ADK agent: an external client sends messages to a central Runner, which orchestrates four surrounding components, Agent Definition, Tools, Session & State, and Long-Term Memory, and is exposed through a serving layer built on FastAPI.](./agent-anatomy.png)

Everything below maps directly onto a piece of that diagram. Read it once next to the picture, and you should be able to point to any box and say which lesson built it and why it's there.

## The Runner: the thing at the center of everything

Start here, since everything else in the diagram exists to be coordinated by it. The Runner is what actually executes one turn of a conversation. It takes your message, sends the conversation so far to the model, and then does whatever the model asks: if the model wants to call a tool, the Runner executes it and feeds the result back; if the model wants to check memory, the Runner routes that too; once the model has a final answer with nothing left pending, the Runner hands that back out. All of this happens as a stream of events, not a single blocking call, tool calls, tool results, partial and final text, callbacks firing, each one arrives as its own event, and the Runner is what keeps that stream moving in the right order.

For six lessons, you never touched a Runner directly, `adk run` and `adk web` built one for you behind the scenes on every single interaction. Lesson 7a took that assumption away and had you build one by hand, specifically so this picture wouldn't have a black box at its center.

## Agent Definition: the identity and the brain

This is the part of an agent you write first, and it's the smallest genuinely mandatory piece. Four things live here:

**Name** identifies the agent, and it has real constraints: it must be a valid Python identifier, and it can't be the literal string `"user"`, since ADK reserves that word for the end user's own input. Once agents start working alongside other agents from Lesson 8 onward, this name is also how one agent refers to another.

**Instruction** is the system prompt, the standing directions that shape everything the agent does: its tone, its scope, what it should refuse, how it should use its tools. Of everything in this box, instruction is the single biggest lever you have over an agent's actual behavior, and you've spent real effort on it in every lesson so far. It can also be templated with `{key}` placeholders that pull live values from session state on every turn, which is exactly how Lesson 6's KYC agent stayed aware of its own progress, and exactly why that lesson's `{kyc_status?}` needed the `?`: an unmarked placeholder for a key that doesn't exist yet raises an error rather than quietly resolving to nothing.

**Description** is a short summary of what the agent does, and unlike instruction, it doesn't affect behavior at all on a standalone agent. It matters the moment an agent has other agents working under it, since a parent agent reads a sub-agent's description to decide whether to hand it a task. Every agent you've built so far has had one, doing nothing yet, waiting for Lesson 8.

**Model** decides which LLM answers on the agent's behalf, and this is the one piece with a real wrinkle worth remembering: Gemini resolves from a plain string, but Claude does not, a bare `"claude-*"` string resolves to a Vertex AI-backed class that expects a GCP project you don't have configured for local development. The fix, wrapping the model in `AnthropicLlm(model="...")` yourself, has come up in nearly every lesson since Lesson 2, and it's worth remembering as the one place ADK's convenience defaults quietly favor its own model family over everyone else's.

One thing that lives inside this same box, though it only showed up once: `output_schema`. Set it to a Pydantic class, and the agent's final answer is constrained to match that exact shape, guaranteed fields, guaranteed types, no free text mixed in, which is what turned Lesson 5's credit risk agent from "writes a paragraph" into "returns a verdict a downstream system can consume directly." It's worth remembering, too, that combining `output_schema` with active tool use, letting an agent call functions and still return a validated final shape, is a comparatively recent capability, one that used to be a hard restriction in earlier ADK releases.

## Tools: how an agent reaches outside itself

An LLM on its own can only produce text. It can't check a real price, run real arithmetic reliably, or touch a database. Tools are what close that gap, and you've now built and used two genuinely different kinds.

**Function tools** are ordinary Python functions you write, with type hints and a docstring, handed to an agent through its `tools` list. ADK builds the tool's schema directly from the function's signature and uses the docstring as the description the model reads to decide when and how to call it, no manual registration, no hand-written JSON schema. Every function tool you've written, from Lesson 3's EMI calculator onward, has followed one more convention worth remembering: always return a dict. It's not strictly mandatory, ADK will wrap a non-dict return in `{"result": ...}` for you, but a dict gives you control over field names, and specifically an `error` key is what ADK's own tool-failure telemetry looks for.

**Built-in tools** are different in kind, not just in name: they're capabilities a model provider runs on its own infrastructure as part of generating a response, `google_search` being the one you've spent the most time with. That's exactly why it's Gemini-only, the search happens inside Google's own model-serving stack, with no equivalent hook for Claude to plug into. When you needed that same grounding capability on Claude, the fix wasn't a workaround for the built-in tool, it was building an ordinary function tool that did the equivalent job with a real search API. That's the general lesson underneath the specific one: built-in tools are fast and convenient but provider-locked; function tools are slightly more work but portable to any model.

## Session & State: memory within one conversation

A session is the container for one ongoing conversation, everything said, on both sides, becomes part of its history as an immutable, chronological event log, exactly what the diagram labels "events (the transcript)." That transcript is the record of what happened.

State is different, and it's easy to conflate the two if you haven't built with both: it's a separate, mutable key-value dictionary attached to the session, for facts an agent needs to track across turns that aren't naturally part of the spoken conversation. Lesson 6's KYC agent used it exactly this way, a tool wrote into `tool_context.state` on every turn, and the agent's own instruction read back a summary of that state through templating, so it always knew what it still needed to ask for.

One detail this recap is a good place to properly introduce, since it came up only in passing before: state keys can carry a prefix that controls how long they live. A plain key like `"kyc_data"` is scoped to the current session alone, gone once that session ends. A key prefixed `user:`, like `"user:risk_tolerance"`, persists across every session that same user has, not just the one it was written in. A key prefixed `app:` is shared globally, visible to every user of the application. Nothing you've built so far has needed anything beyond plain, session-scoped keys, but this scoping is what lets state reach further than a single conversation without reaching all the way to a full memory service, a middle ground worth knowing exists.

Behind both events and state sits a `SessionService`, the pluggable component actually responsible for storing and retrieving them. `adk run` and `adk web` default to one backed by local SQLite, which is why, as corrected back in Lesson 6, your sessions survive closing and reopening the CLI. Lesson 7a's `main.py` used a different one, `InMemorySessionService`, created once and shared across every request for the life of that process, which is exactly what let separate HTTP calls continue the same conversation.

## Long-Term Memory: reaching past a single session

Session state disappears the moment a session ends. Memory is ADK's answer to what happens when you need continuity past that point, a relationship manager recalling a client's stated preferences weeks later, in a conversation the agent has no session-level record of at all.

A `MemoryService` is the component behind this, with two operations doing the real work: `add_session_to_memory`, which takes a session's content and stores it in a searchable archive, and `search_memory`, which takes a query and returns whatever's relevant across everything stored for that user, regardless of which session it originally came from. `load_memory`, the tool an agent actually calls to use this, is worth remembering for the same reason `google_search` was worth remembering: it's a plain function tool, not a provider built-in, so it works identically on Claude as it would on any other model, no workaround required.

Lesson 7's relationship manager triggered `add_session_to_memory` automatically through an `after_agent_callback`, a function ADK runs after every agent turn without you calling it manually. That's also where a real, easy-to-miss distinction lives: ADK's default memory service is genuinely in-memory, it resets on every process restart, even though the default session service, as just covered, persists to disk. Testing memory recall meant working across two sessions inside one continuously running process, not across two separate launches of the CLI.

One related component worth naming even though nothing you've built has used it yet: **artifacts**, for storing larger binary objects, files, documents, generated during a session, backed by their own `ArtifactService` and reachable through `tool_context.save_artifact()`. It's a genuinely distinct concept from state, state holds small values you'd be comfortable printing to a terminal; artifacts hold the kind of thing you wouldn't. It's part of the full picture, flagged honestly as ground this series hasn't covered hands-on.

## The Serving Layer: how any of this reaches a real user

Every component above can exist and still never be reachable by anyone outside a terminal. The serving layer is what changes that: `main.py`, a FastAPI application holding one shared `SessionService` for as long as the process runs, with a `/chat` endpoint that does nothing more than parse an incoming request, hand it to the Runner, and return whatever comes back. Lesson 7a proved this layer doesn't care who's calling it by pointing two completely different clients at the same endpoint, a Streamlit web UI and a bare console script, neither of which has any idea ADK exists underneath.

## What this picture doesn't show yet

Look closely at the diagram and you'll notice every box describes one agent. One model, one instruction, one set of tools, one Runner coordinating all of it. That's been true of every single thing you've built through Lesson 7a, and it's about to stop being true.

Real systems rarely stay this simple. A loan application might need one specialist for risk scoring, another for compliance checks, another for making the final call, each with a narrower job and a sharper instruction than any one agent trying to do all three at once. Coordinating several agents like that, deciding which one runs when, what passes between them, how failures in one affect the others, is a distinct problem from anything in this recap, and it's the entire subject of what comes next.

Lesson 8 starts that shift with `SequentialAgent`, `ParallelAgent`, and `LoopAgent`, ADK's primitives for chaining specialist agents into a fixed, predictable pipeline. Later lessons go further still: a full graph-based workflow runtime for branching, conditional logic, and human-in-the-loop approval steps, and eventually agent-to-agent delegation, where one agent can hand work to another that might be running as an entirely separate service. Every one of those builds on exactly the anatomy in this lesson's picture, just with more than one of these circles on the page at once.
