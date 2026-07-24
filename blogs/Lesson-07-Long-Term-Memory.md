# Lesson 7: Long-Term Memory

Lesson 6 gave an agent memory within a single conversation. This lesson extends that past a single conversation entirely, to a relationship manager assistant that needs to recall what a client told it days or weeks ago, in a completely separate session.

## The problem we're solving

A private wealth management relationship manager builds a real relationship with a client over many separate conversations: a call today, a follow-up email thread next week, a portfolio review next month. If a client mentioned three weeks ago that they want strictly conservative, low-risk investments and have a strong interest in ESG (environmental, social, and governance) funds, a good relationship manager doesn't make them repeat that on every call. An AI assistant standing in for part of that relationship needs the same continuity, and Lesson 6's session state can't provide it, since state disappears the moment a session ends.

## Session and state versus memory

Here's the distinction that matters for this lesson: session state, from Lesson 6, is scoped to one conversation. It's gone once that conversation is over, or at best it's tied to one `session_id` that a specific chat window keeps reusing. Memory, in ADK's sense, is different: it's a searchable archive that spans *across* separate sessions for the same user, built specifically so information from an old conversation can resurface in a brand new one.

Two operations matter here. `add_session_to_memory` takes a session (usually a finished or in-progress one) and stores its content in that searchable archive. `search_memory` takes a text query and returns whatever relevant content it can find across everything that's been stored for that user, regardless of which session it originally came from. ADK also ships a ready-to-use tool, `load_memory`, that wraps `search_memory` as something an agent can call mid-conversation, the same way it calls any other function tool.

That last point is worth pausing on, given what we ran into in Lesson 4. Unlike `google_search`, `load_memory` is not a Gemini-only built-in. It's implemented as a plain `FunctionTool`, so it works identically regardless of which model is running the agent, Claude included, with no special wrapping or workaround needed.

**One thing worth knowing before you build this:** ADK's default memory service, `InMemoryMemoryService`, does true in-memory keyword search, no persistence, and it resets completely every time the process restarts, unlike the session storage we corrected a moment ago in Lesson 6. This is a real, deliberate contrast: `adk run`/`adk web` persist *sessions* to local SQLite by default, but they never persist *memory* that way unless you explicitly configure a different memory backend. That means we can't demonstrate this lesson's "recall across sessions" by closing and reopening `adk run`, doing that would wipe the memory right along with it. We need two separate sessions inside one continuously running process instead, which is exactly why this lesson uses `adk web`.

## Step 1: Build the relationship manager agent

Create the folder:

```bash
mkdir -p agents/lesson07_relationship_manager
```

Create `agents/lesson07_relationship_manager/agent.py`:

```python
"""BFSI Lesson 7: Long-Term Memory.

A relationship manager assistant for a wealth management desk. It
saves every conversation to long-term memory automatically, and can
search that memory to recall a client's stated preferences even in a
brand new session where nothing has been said yet.
"""

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import load_memory

from common.model_config import get_model


async def save_conversation_to_memory(callback_context: CallbackContext) -> None:
    """Saves the current session's conversation to long-term memory.

    Runs automatically after every agent turn, so anything a client
    says becomes searchable in future sessions almost immediately,
    without requiring a separate manual step.

    Args:
        callback_context: Injected automatically by ADK. The parameter
            must be named exactly "callback_context"; ADK enforces
            this for callback functions.
    """
    await callback_context.add_session_to_memory()


AGENT_INSTRUCTION = (
    "You are a relationship manager assistant for a wealth management "
    "desk. Clients may have shared preferences, goals, or constraints "
    "in earlier conversations that aren't visible in this one. Before "
    "giving investment-related suggestions, use the load_memory tool "
    "with a query describing what you're about to discuss, to check "
    "whether this client has stated relevant preferences before, such "
    "as risk tolerance, sector interests, or specific requirements. "
    "If memory search returns nothing relevant, proceed using only "
    "what the client has told you in this conversation. Always be "
    "clear that you are not providing personalized investment advice, "
    "only general information, since that requires a licensed advisor."
)

root_agent = Agent(
    name="relationship_manager_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description=(
        "Wealth management relationship manager assistant that "
        "recalls client preferences across separate conversations."
    ),
    tools=[load_memory],
    after_agent_callback=save_conversation_to_memory,
)
```

Create `agents/lesson07_relationship_manager/__init__.py`:

```python
from . import agent
```

Two new pieces here. `after_agent_callback=save_conversation_to_memory` registers a function ADK runs automatically after every agent turn completes, no manual trigger needed. Inside it, `callback_context.add_session_to_memory()` is the actual save: it hands the current session's content to whatever memory service is configured, `InMemoryMemoryService` by default. ADK enforces that this callback's parameter is named exactly `callback_context`; naming it anything else will fail. We're saving after every single turn rather than waiting for some notion of "session end," partly because a chat session doesn't have a clean, detectable end point in this setup, and partly because it means a client's preferences become recallable almost immediately rather than only after we remember to save them.

`load_memory` in the `tools` list is what lets the agent actually use that saved history. The instruction tells it explicitly when to reach for it, before making any suggestion, since a model won't reliably think to check memory on its own just because the tool exists.

## Step 2: Run it across two sessions

```bash
uv run adk web agents
```

Select `lesson07_relationship_manager`. This first conversation establishes the client's preferences:

```
I prefer conservative, low-risk investments, and I'm particularly interested in ESG and sustainable funds.
```

Let the agent respond normally. That turn just got saved to memory automatically, courtesy of the callback.

Now, **without restarting the server**, start a new session for the same agent. In `adk web`'s sidebar, use the session switcher to create a new conversation rather than closing and reopening the app, this keeps the same running process, and therefore the same in-memory memory service, alive underneath both sessions. In that new, empty session, ask something that doesn't repeat any of what you just said:

```
What would you suggest I look at for my portfolio this quarter?
```

You should see the agent call `load_memory` with something like a risk-preference or ESG-related query, and its answer should reflect what you told it in the *previous* session, steering toward conservative, ESG-aligned suggestions, even though this session's own history has no memory of that conversation at all. That's the actual proof this lesson is after: a completely fresh session producing an answer shaped by a conversation it never directly saw.

## If you're coming from LangChain or LangGraph

This is conceptually close to a RAG (retrieval-augmented generation) setup you might have built yourself in LangChain: store conversation content somewhere searchable, then retrieve relevant pieces back into context on a later query. The difference is how much of that ADK does for you here. In LangChain, you'd typically choose and wire up a vector store, write the retrieval query logic, and decide when to trigger storage yourself. ADK's `MemoryService` interface, `add_session_to_memory` and `search_memory`, standardizes that pattern into two operations behind a common interface, so swapping the in-memory keyword-search implementation we used here for a production-grade vector-search-backed one later is a configuration change to the service, not a rewrite of the agent.

## In this lesson

We gave an agent memory that survives past a single conversation. The relationship manager assistant automatically saves what a client tells it, via a callback that fires after every turn, and can recall that information in an entirely separate session using the `load_memory` tool, itself a plain, portable function tool that works the same way on Claude as it would on Gemini. We also confirmed something worth remembering as this series continues: ADK's default local setup persists session state to disk, but not memory, a distinction that matters the moment you're testing anything memory-related.

## In the next lesson

Lesson 8 is where this series moves from single agents to real multi-agent systems, and it's also where we step away from `adk run`/`adk web` as our primary way of running things. We'll build a loan underwriting pipeline with `SequentialAgent`, `ParallelAgent`, and `LoopAgent`, and start driving it with our own `Runner` in a `main.py`, since a multi-step pipeline is something we generally want to run end-to-end and inspect, not conduct as a back-and-forth chat.
