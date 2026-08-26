# ADK BFSI Tutorial Series — Series Bible (Non-Workflows Track)
## Context Document for Continuing in a New Chat: Capstones and GCP Deployment

This document gives a new Claude instance everything it needs to build 2-3 real BFSI capstone projects and their GCP deployment, using only what Lessons 1 through 15 covered. Workflows (Lesson 16 onward) do not exist for this chat. Treat this document as the complete history of a project that stopped at Lesson 15a.

---

## 1. Series Overview

**Title:** Building BFSI Agents with Google ADK 2.x
**Target audience:** Mid-level Python developers. Assume the reader knows Python and may know LangChain or LangGraph, but is new to ADK. Write as if tutoring a smart developer, conversational, honest, no fluff.
**Domain:** Every example is BFSI (Banking, Financial Services, Insurance) unless explicitly noted. Real problems, real data sources where free and legal (`yfinance`, `api.mfapi.in`, Stripe test mode, Tavily), synthetic data clearly labeled as synthetic when real data isn't available.
**Target readers:** India, US, and EU users. Use INR for Indian examples, USD/EUR where relevant.
**ADK version:** `google-adk==2.5.0`. This is the authoritative, pinned version. Always verify claims against the real installed package before writing anything, never from memory or assumption.
**Project root folder:** `adk2_tutorial/`.

This chat's specific goal: build 2 to 3 real BFSI capstone projects using only concepts from Lessons 1 through 15, then deploy them to GCP, run them there, and tear them down immediately. No `Workflow` class, no graph-based orchestration, anywhere in this chat.

---

## 2. Model Policy (Non-Negotiable)

| Priority | Model | Use when |
|---|---|---|
| 1st | `claude-haiku-4-5-20251001` | Default for all agents. Always try Haiku first. |
| 2nd | `claude-sonnet-4-5` | Only when Haiku measurably fails (complex reasoning, multi-step routing). Call this out explicitly when escalating. |
| 3rd | `gemini-flash-latest` | Only when a built-in tool requires it (`GoogleSearchTool`, for example). Never default to Gemini. |
| Excluded | Claude Opus | Never required. |

**How Claude is used in ADK:** Never pass `"claude-*"` as a bare string. Bare strings route to Vertex AI and fail. Always:
```python
from google.adk.models.anthropic_llm import AnthropicLlm
model = AnthropicLlm(model="claude-haiku-4-5-20251001")
```

**Why no LiteLLM:** Dropped early due to Rust build issues on Windows. ADK's native Anthropic provider is used instead. Do not reintroduce it.

**Model config lives in:** `agents/common/model_config.py`, a `get_model(tier: str = "primary")` helper every agent imports. Never hardcode model strings in individual agent files.

---

## 3. Project Structure

```
adk2_tutorial/
├── .env
├── .gitignore
├── .python-version
├── pyproject.toml
├── agents/
│   ├── common/
│   │   ├── __init__.py
│   │   ├── model_config.py        ← get_model() helper
│   │   ├── runner_utils.py        ← get_or_create_session(), run_agent_query()
│   │   └── callbacks.py           ← reusable callbacks
│   ├── lesson02_first_agent/
│   ├── lesson03_loan_tools/
│   ├── lesson04_market_briefing/
│   ├── lesson05_credit_risk/
│   ├── lesson06a_sessions_and_state/
│   ├── lesson06b_sessions_and_state/
│   ├── lesson06c_artifacts/
│   ├── lesson07a_callbacks/
│   ├── lesson07b_long_running_tools/
│   ├── lesson08_long_term_memory/
│   ├── lesson09_production_serving/
│   ├── lesson11a_sequential_agent/
│   ├── lesson11b_parallel_agent/
│   ├── lesson11c_loop_agent/
│   ├── lesson11d_agent_tool/
│   ├── lesson12_human_in_the_loop/
│   ├── lesson13a_skills/
│   ├── lesson14a_mcp/
│   ├── lesson14b_mcp_server/
│   └── lesson15a_a2a/
└── .vscode/
```

---

## 4. Lesson Folder Conventions

From Lesson 6a onward, lessons use a nested structure with their own `main.py`:
```
agents/lessonNN_topic/
├── agent_name/
│   ├── __init__.py    ← from . import agent
│   ├── agent.py        ← agent definition ONLY, no business logic
│   ├── tools.py         ← tool functions, lesson-local
│   └── callbacks.py     ← callbacks, if domain-specific
└── main.py              ← drives the lesson, console loop
```

`main.py` inserts the project's `agents/` folder onto `sys.path` so `common.*` resolves, and inserts its own lesson folder so lesson-local modules resolve:
```python
THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))   # adds agents/ for common.*
sys.path.insert(0, str(THIS_DIR))          # adds this lesson's own folder
```

**Multi-agent lessons (11a onward) don't always nest sub-agents under one shared parent.** The exact shape varies by what's actually being demonstrated:
- When sub-agents are purely internal building blocks of one pipeline, they sit in their own subfolder under the orchestrator (for example `risk_specialist/` inside `lesson13a_skills/skills_demo/`).
- When two agents genuinely represent two separate roles that could run as separate processes (an MCP server and its consumer, an A2A server and its consumer), they get separate top-level folders inside the same lesson, not nested inside one another. Examples: `lesson14b_mcp_server/nav_server/` and `nav_consumer/`; `lesson15a_a2a/risk_specialist/` (the agent definition), `risk_service.py` (the standalone A2A server script at the lesson's top level), and `loan_orchestrator/` (the consumer).

**adk web discovery:** for a folder to show up in `adk web`, it needs a real subpackage with its own `agent.py` defining a `root_agent` variable. A flat file at the lesson root is not enough. A standalone server script (an MCP server, an A2A server) deliberately has no `root_agent`, since it's meant to run on its own via `uv run`, not through `adk web`. Selecting it in `adk web` will fail, and that's expected, worth a line in the lesson saying so.

**When to use `adk run`/`adk web` versus `main.py`:**
- Lessons 2 through 5: `adk run agents/lessonNN_name` or `adk web agents`.
- Lesson 6a onward: `uv run agents/lessonNN_topic/main.py` is the primary path. `adk web agents` is also shown as a secondary way to try most lessons, each such lesson lists which subfolder to select.

---

## 5. Code Conventions (All Lessons)

### File organization
- `agent.py`: agent declaration only, model, instruction, description, tools list, callback registrations. No business logic.
- `tools.py`: tool function implementations. Lesson-local tools stay here; reusable tools go in `agents/common/`.
- `callbacks.py`: callback implementations, same local-versus-common split as tools.
- `main.py`: `Runner`, `SessionService`, and any other service wiring, plus the console loop or demo script.

### Docstrings
Google docstring format throughout. Every tool function needs a docstring with Args and Returns, the model uses the whole docstring as the tool's description.

### File headers
```python
"""Lesson N: Short description.

Longer explanation.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""
```
Do not prefix with "BFSI", just "Lesson N: ...".

### Tool conventions
- Always return a dict with named fields.
- Include an `"error"` key for failure cases.
- If a tool calls an `async` ADK method, the tool itself must be `async def`.
- Wrap slow operations in `LongRunningFunctionTool(fn)`.
- Never call `asyncio.get_event_loop().run_until_complete()` inside a sync tool, make the tool async instead.
- Where a tool's output should be deterministic for teaching purposes rather than random, derive it from a hash of the input (`hashlib.sha256`), not `random`. This keeps worked examples reproducible across runs.

### Console input in async loops
Never use bare `input()` inside `async def`:
```python
loop = asyncio.get_event_loop()
try:
    user_input = await loop.run_in_executor(None, lambda: input("You: "))
except EOFError:
    break
```

### load_dotenv
Every `main.py`, and every standalone server script, calls `load_dotenv(override=True)` before any ADK imports.

### common/runner_utils.py, exact shape to reuse everywhere
```python
from google.adk.runners import Runner
from google.genai import types

async def get_or_create_session(session_service, app_name, user_id, session_id):
    session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    if session is None:
        session = await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    return session

async def run_agent_query(agent, app_name, user_id, session_id, query, session_service, memory_service=None):
    session = await get_or_create_session(session_service, app_name, user_id, session_id)
    runner = Runner(app_name=app_name, agent=agent, session_service=session_service, memory_service=memory_service)
    user_message = types.Content(role="user", parts=[types.Part(text=query)])
    text_segments = []
    async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=user_message):
        if event.content and event.content.parts:
            text = "".join(part.text for part in event.content.parts if part.text)
            if text:
                text_segments.append(text)
    return "\n\n".join(text_segments) if text_segments else "(no response received)"
```
This collects every text segment across a turn, not just the last "final response" event, since a turn can legitimately produce more than one text-bearing event (a tool call followed by a separate closing remark, for example). Always import and reuse this exact helper. Never write inline `Runner`/session boilerplate when this already does the job. Always capture and use its return value, never discard it silently.

### common/model_config.py
```python
from google.adk.models.anthropic_llm import AnthropicLlm

def get_model(tier: str = "primary"):
    return AnthropicLlm(model="claude-haiku-4-5-20251001")
```

---

## 6. Lesson Structure Template

```
# Lesson N: Title

[1-2 sentence callback to the previous lesson]

## What we're building
[Plain-language description of the real scenario, before any technical
framing. What problem, whose problem, why it matters. No code yet.]

## [Concept introduction, when genuinely new]
[Theory for new ADK concepts. Use NOTE: callouts for caveats.
Introduce every term before it's used in code, never the reverse.]

## Step 1: [First concrete step]
[Code, folder path clearly shown. Explanation follows every code
block, never leave one unexplained.]

## Step N: Run it
[Exact command. Describe what the reader will see, general shape not
exact output where output is non-deterministic. Sample prompts to try.]

## If you're coming from LangChain or LangGraph
[Real, checked comparison, not a guess]

## In this lesson
[Summary, always this exact heading]

## In the next lesson
[Lead with WHAT, then HOW. Never say "Lesson N", say "the next lesson".]
```

**Additional rules, several accumulated hard during Part 2:**
- Every code block gets explanation immediately after it. No exceptions.
- Back-reference previous lessons by name and number together, "Back in Lesson 6a we covered...", not just a number.
- Use `> **NOTE:** ...` blockquote format for caveats.
- Never introduce a term, a class name, or a forward reference to a later lesson before it has actually been explained. Check this specifically before finalizing any lesson, it has been a repeated, real bug.
- When a lesson shows a full-disclosure list of fields or options (a config object, a frontmatter schema), separate what's functionally load-bearing from what's optional-but-inert. Don't give equal visual weight to a field that does nothing yet.
- If a worked example uses a specific real API or dataset, verify it live before writing about it. If it can't be verified live in the working environment (no API key, network restricted), say so plainly in the lesson, once, without turning it into a running disclaimer.

---

## 7. Standing Instructions (Accumulated Across Both Parts)

**Tone and style:**
- Conversational, like a knowledgeable person tutoring you, not formal documentation.
- Direct. Simple English. Short sentences. Avoid stacking too many clauses with commas.
- No em-dashes, ever.
- No "not only X but also Y". No forced metaphors or clichés.
- No emojis unless the reader uses them first.
- Address the reader as "you/your".
- Think like a senior architect planning the lesson. Code like a senior developer. Write like a mentor teaching a newbie who may or may not know LangGraph or LangChain.

**Content rules:**
- Never introduce a named concept, class, or method without explaining it the first time it's used.
- Never use something in code before introducing it in prose.
- A brief reminder is fine for something covered earlier, don't assume the reader memorized every detail, but don't re-teach it either.
- State honest caveats and known limitations plainly. Never claim something works without having verified it.
- Never let Claude's own research, investigation, or verification process leak into lesson text. No "I confirmed", "I tested", "I checked", "confirmed directly", anywhere in a lesson. State facts plainly. That process belongs in chat, not in the deliverable.
- Never let the back-and-forth discussion between Claude and the reader leak into lesson text either. A lesson reads as if only the final, agreed approach was ever considered, no trace of alternatives rejected or corrections made along the way.
- When Claude changes something after feedback, always state plainly what changed, old versus new, in the chat response. Don't just make the change and let the reader go find it.

**Code rules:**
- All code must run without errors. Verify before including it, live where the environment allows.
- Complete code listings, never trail off with "..." mid-function.
- No hardcoded API keys or secrets, ever.
- Break large code blocks into small, meaningful functions.
- Inline comments for non-obvious lines only.
- Always reuse `agents/common/model_config.py` and `agents/common/runner_utils.py`. Never reinvent this boilerplate per lesson.
- Always capture and display a function's or a tool's return value. Never silently discard it.

**Lesson generation process:**
- Generate one lesson at a time. Wait for an explicit go-ahead before the next one.
- If a lesson has issues, fix before moving on.
- When asked to fix something, fix only what was asked, don't regenerate the whole lesson unless asked to.
- For any genuinely new or unverified topic, pause, verify first, then present a short plan for confirmation before writing the full lesson.

**On errors found during development:**
- The reader codes along in real time. If they report an error, debug it properly against the real ADK source, don't guess.
- If a fix needs changes to an already-generated lesson file, apply a targeted edit to just the relevant section, not a full regeneration, unless the scope genuinely requires it.

**Verification discipline, non-negotiable:**
- Never write ADK code from memory or assumption. Check the actually installed package first.
- Test code for real wherever the environment allows. Where a live LLM call can't be completed (no API key), verify everything up to that boundary, imports, construction, protocol-level behavior, deterministic logic, and say plainly where the untestable boundary sits.
- Anything a third-party AI (Gemini, or a prompt someone else wrote) claims about ADK internals must be independently verified before being trusted. This has repeatedly turned out to be wrong, invented module paths, invented methods, invented behavior that doesn't exist.

**LangChain/LangGraph comparisons:**
- Include wherever there's a meaningful, checked parallel.
- Always use the exact heading "If you're coming from LangChain or LangGraph".
- Don't build a whole lesson's framing around this audience. Write clean for everyone, then place a comparison note right next to the specific feature it concerns, not concentrated at the end.

**GCP deployment (the actual next phase for this chat):**
- Prefer free tier or cheapest services first.
- Every deploy script must have a paired teardown script.
- Cloud Run is the preferred compute, cheapest, scales to zero.
- Flag approximate costs before any step that incurs meaningful spend.
- Deploy, demonstrate it running, then tear down immediately, don't leave paid resources running between sessions.

---

## 8. The agents/common Folder, Key Shared Files

### agents/common/model_config.py
`get_model(tier: str = "primary")`, returns `AnthropicLlm(model="claude-haiku-4-5-20251001")`. Used by every lesson agent from Lesson 3 onward.

### agents/common/runner_utils.py
`get_or_create_session(...)` and `run_agent_query(...)`, exact shape given in section 5. This is the one helper every single lesson's `main.py` should import and reuse, never reimplement.

### agents/common/callbacks.py
Generic reusable callbacks, created in Lesson 7a.

---

## 9. Key Technical Facts, Verified Against Real ADK 2.5.0 Source

**From Part 1:**
- `AnthropicLlm(model="...")` required for Claude, never a bare string.
- `GoogleSearchTool(bypass_multi_tools_limit=True)` needed to combine `google_search` with other tools. Still Gemini-only regardless of the flag.
- `output_schema` plus `tools` on the same agent works, but has been unreliable specifically with Claude, output_schema plus tools can trigger a `SetModelResponseTool` fallback that doesn't always resolve cleanly. When this happens, prefer having the tool write directly to `tool_context.state[key] = result` instead of relying on `output_schema`/`output_key`.
- `output_key="key_name"` on `Agent` writes the validated result to session state after every turn automatically.
- `save_artifact`/`load_artifact` on `ToolContext` are async, the tool must be `async def`.
- `InMemoryMemoryService` and `InMemorySessionService` reset on process exit, pure RAM, not SQLite.
- Callback parameter names are enforced as keyword arguments. A wrong name is a `TypeError` at runtime, not at import time.
- `before_model_callback`/`after_model_callback` fire once per model call, not once per turn, a turn with tool calls involves multiple model calls.
- `tool_context.state["key"] = value` needs a full reassignment. In-place mutation of a nested object doesn't persist.

**From Part 2, Lessons 11 through 15a:**
- `SequentialAgent`, `ParallelAgent`, `LoopAgent` each do exactly one fixed thing, no branching, no mixing shapes. This distinction matters again once Workflows are reintroduced in a later, separate chat, but is not itself part of this chat's scope.
- `AgentTool` wraps a whole agent as a tool. The wrapped agent's model does not need to match the calling agent's model, `AgentTool.run_async` creates its own isolated `Runner` and session.
- `ResumabilityConfig` for Human-in-the-Loop is marked experimental directly in ADK's own source. Real, working, but flagged as subject to change.
- `SequentialAgent` genuinely tracks resume position (`SequentialAgentState`, `start_index`), a resumed decision routes to the specific sub-agent that made the paused call, not the wrapping `SequentialAgent`. A pipeline with steps after the paused one needs to be driven explicitly on resume, not assumed to continue automatically.
- ADK's own Skills system (`google.adk.skills`, `SkillToolset`) follows the same open `agentskills.io` spec Claude's own Skills feature does, independently designed, converging on the same shape, `SKILL.md` with frontmatter, layered loading (L1 name/description, L2 full instructions, L3 references/assets/scripts).
- A skill's `metadata.adk_additional_tools` names tools from `SkillToolset`'s own `additional_tools` pool that become available only once that skill loads. These tools are plain Python functions defined in your own regular code, not files inside the skill's own folder. `scripts/` inside a skill folder is a different thing entirely, real executable code the model runs via `RunSkillScriptTool`, not something `adk_additional_tools` points at.
- The `allowed-tools` frontmatter field exists in the open spec but is not acted on by ADK 2.5.0 at all, parsed and stored, nothing more.
- `load_skill_resource` reads real content from a skill's `references/`/`assets/`/`scripts/` folders. Text content returns directly; binary content is injected into the model's context separately. A resource lookup that fails twice in one invocation returns a `RESOURCE_NOT_FOUND_FATAL` error telling the model explicitly not to retry.
- `UnsafeLocalCodeExecutor` is the only zero-setup code executor for scripted skills, runs generated code directly in your own process, no sandbox, fine for a controlled lesson environment, not for production or untrusted input.
- MCP: `google-adk[mcp]` is the correct install, not bare `pip install mcp`, which can pull an unrelated package. `StdioConnectionParams` for local servers, `StreamableHTTPConnectionParams` for remote, `SSE` is deprecated. `McpToolset` resolves tools the same way any other toolset does, fresh each turn.
- A real, working pairing exists between Skills and MCP: `SkillToolset`'s `additional_tools` parameter accepts a whole `BaseToolset`, including an `McpToolset`, and a skill's `adk_additional_tools` can name specific tools out of that remote server's surface, gating a large external tool set down to exactly what one skill needs.
- Alpha Vantage's real MCP server requires OAuth with no documented simple-key alternative for headless, agentic use. Stripe's official server does document a bearer-token path specifically for autonomous agents, that's why the MCP-consuming lesson uses Stripe, not Alpha Vantage.
- `google-adk[a2a]` needs `sse_starlette` as a separate dependency for serving an agent over A2A, not pulled in automatically. Only needed for serving, `RemoteA2aAgent` alone (consuming) does not need it.
- `to_a2a()` auto-generates a real Agent Card from an agent object. The actual served card differs from a naive reading of the A2A spec types, the endpoint URL sits inside `supportedInterfaces`, not a flat `url` field, and `skills` in the card is one entry per tool plus one for the agent's own instructions, not one clean hand-shaped entry.
- A2A's own `skills` field on an Agent Card is unrelated to ADK's Skills system, same word, two unrelated concepts from two different specifications.
- The A2A task lifecycle is a real state machine: `SUBMITTED`, `WORKING`, `COMPLETED`, `FAILED`, `CANCELED`, `REJECTED`, `INPUT_REQUIRED`, `AUTH_REQUIRED`. `INPUT_REQUIRED` is the protocol-level version of the pause-and-resume problem Lesson 12 solved by hand.
- `RemoteA2aAgent` is itself a `BaseAgent`, so everything about `AgentTool` and sub-agent composition applies to it unchanged, it can be wrapped in `AgentTool` for a model's own delegation judgment, or used directly as a plain sub-agent in a `SequentialAgent` for a step that always runs.
- An MCP server has no model or reasoning of its own, it's a deterministic tool executor. An A2A server does have its own full LLM-driven agent on the other end. Easy to conflate, genuinely different things.

---

## 10. Packages Added to the Project, Cumulative

```bash
uv add google-adk==2.5.0
uv add anthropic python-dotenv pyyaml    # Lesson 1
uv add yfinance                          # Lesson 4, and reused later for global mutual fund data
uv add tavily-python                     # Lesson 4
uv add reportlab                         # Lesson 6c
uv add fastapi uvicorn streamlit requests # Lesson 9
uv add "google-adk[mcp]==2.5.0"          # Lesson 14
uv add httpx                             # Lesson 14b, real HTTP calls to api.mfapi.in
uv add "google-adk[a2a]==2.5.0" sse_starlette  # Lesson 15
```

No LiteLLM anywhere. `.env` needs `TAVILY_API_KEY` for Tavily search and `STRIPE_SECRET_KEY` (test mode) for the MCP-consuming lesson.

---

## 11. Complete Lesson Sequence, 1 Through 15a

| # | Title | Key concept |
|---|---|---|
| 1 | Environment Setup | uv, ADK install, API keys, project config |
| 2 | Your First Agent | `Agent`, `AnthropicLlm`, `adk run`, `adk web` |
| 3 | Function Tools | Plain functions as tools, docstring-derived schemas, dict returns |
| 4 | Built-in Tools & Grounding | `GoogleSearchTool`, Tavily, the Gemini-only limitation |
| 5 | Structured Output | `output_schema`, Pydantic, `output_key` |
| 6a | Sessions & State, Agent View | `SessionService`, `Session`, `Runner`, pre-seeded state |
| 6b | Sessions & State, Tool View | `ToolContext`, tool-driven state |
| 6c | Artifacts | `ArtifactService`, `save_artifact`, `load_artifact`, async tools |
| 7 | Callbacks, Theory | All six callback types, firing order |
| 7a | Callbacks in Practice | Real callbacks wired on a working agent |
| 7b | Long-Running Tools | `LongRunningFunctionTool`, async event collection |
| 8 | Long-Term Memory | `MemoryService`, `load_memory`, `add_session_to_memory` |
| 9 | Production Serving | FastAPI, `runner_utils.py`, Streamlit, console client |
| 10 | Anatomy of an Agent | Full single-agent recap, theory only |
| 11 | Multi-Agent Theory | `SequentialAgent`, `ParallelAgent`, `LoopAgent`, theory only |
| 11a | SequentialAgent in Practice | Loan underwriting pipeline |
| 11b | ParallelAgent in Practice | Parallel checks feeding a sequential decision |
| 11c | LoopAgent in Practice | Retry loop with a deterministic pass/fail check |
| 11d | AgentTool | Wrapping a whole agent as a callable tool |
| 12 | Human-in-the-Loop | `LongRunningFunctionTool` plus `ResumabilityConfig`, pause and resume by hand |
| 13 | Skills, Theory | `SKILL.md`, layered loading, `SkillToolset`, comparison with a shared `tools.py` |
| 13a | Skills in Practice | Three real skills, zero-tools, tool-gating, and scripted |
| 14 | MCP Servers, Theory | Consuming versus building, transports, auth |
| 14a | MCP Consuming | Real agent connected to Stripe's official server |
| 14b | MCP Building | Real server serving Indian and global mutual fund data |
| 15 | A2A, Theory | Agent Card, serving and consuming, task lifecycle |
| 15a | A2A in Practice | Real risk agent served and consumed two ways |

Lesson 16 and everything after it (Graph-Based Workflows) is out of scope for this chat entirely.

---

## 12. What Comes Next in This Chat: Capstones and GCP Deployment

The plan from here, not yet built, no content decided:

1. **2 to 3 real BFSI capstone projects**, each combining several concepts from Lessons 1 through 15 into one coherent, realistic system. Multi-agent orchestration, Skills, MCP, A2A, HITL, memory, callbacks, artifacts, all fair game, in whatever combination a real capstone scenario actually calls for. No `Workflow` class anywhere.
2. **GCP deployment for these capstones.** Deploy, run for real, verify it works, then tear down immediately. Cloud Run preferred, free tier first, every deploy script paired with a teardown script, costs flagged before anything that spends money.

Nothing about the capstones' scope, scenarios, or structure is decided yet. Follow the same process this whole series has used for every new major topic: verify what's needed against real source first, propose a plan, get confirmation, then build.

---

## 13. Uploaded Lesson Files, When Provided

If the reader uploads lesson files as their own offline-edited final versions, those are the authoritative source for what a lesson actually contains, not anything reconstructed from this bible document. Expected filenames, matching the sequence in section 11:

Lesson-01 through Lesson-10 (as listed in the original Part 1 bible), plus:
Lesson-11-Multi-Agent-Theory.md, Lesson-11a through 11d practice files, Lesson-12-Human-in-the-Loop.md, Lesson-13-Skills-Theory.md, Lesson-13a-Skills-in-Practice.md, Lesson-14-MCP-Servers-Theory.md, Lesson-14a-MCP-in-Practice.md, Lesson-14b-Building-an-MCP-Server.md, Lesson-15-Agent-to-Agent-Theory.md, Lesson-15a-Agent-to-Agent-in-Practice.md.

When a future response in this chat references a previous lesson, refer to an uploaded file as ground truth if one exists for that lesson. If none is uploaded, this bible's own summary in section 11 and the technical facts in section 9 are the best available reference.
