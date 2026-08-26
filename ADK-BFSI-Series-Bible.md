# ADK BFSI Tutorial Series — Series Bible
## Context Document for Continuing in a New Chat

This document gives a new Claude instance everything it needs to continue this tutorial series from Lesson 11 onward, as if it were the same conversation. It covers: what we've built, how we build it, all standing instructions, and the full lesson sequence past and future.

---

## 1. Series Overview

**Title:** Building BFSI Agents with Google ADK 2.x  
**Target audience:** Mid-level Python developers. Assume reader is familiar with Python and LangChain/LangGraph but new to ADK. Write as if tutoring a smart developer — conversational, honest, no fluff.  
**Domain:** Every example is BFSI (Banking, Financial Services, Insurance) unless explicitly noted. Real problems, real data sources (yfinance, Tavily, reportlab etc.), no toy examples.  
**Target readers:** India, US, and EU users. Use INR for Indian examples, USD/EUR where relevant.  
**ADK version:** 2.5.0 (Google ADK Python). This is the authoritative version.  
**Project root folder:** `adk2_tutorial/` (not `adk-bfsi-lab` — this was a mid-series correction).

---

## 2. Model Policy (Non-Negotiable)

| Priority | Model | Use when |
|---|---|---|
| 1st | `claude-haiku-4-5-20251001` | Default for all agents. Always try Haiku first. |
| 2nd | `claude-sonnet-4-5` | Only when Haiku measurably fails (complex reasoning, graph routing). Explicitly call this out when escalating. |
| 3rd | `gemini-flash-latest` | Only when a built-in tool requires it (e.g. `google_search`/`GoogleSearchTool`). Never default to Gemini. |
| Excluded | Claude Opus | Never required. May note "would benefit from Opus" but never make it a requirement. |

**How Claude is used in ADK:** Never pass `"claude-*"` as a bare string. Bare Claude strings route to Vertex AI and fail. Always use:
```python
from google.adk.models.anthropic_llm import AnthropicLlm
model = AnthropicLlm(model="claude-haiku-4-5-20251001")
```

**Why no LiteLLM:** LiteLLM was dropped early due to Rust build issues on Windows. ADK's native Anthropic provider (`google.adk.models.anthropic_llm`) is used instead. Do not reintroduce LiteLLM.

**Model config lives in:** `config/models.yaml` — a shared YAML file that every agent reads via `agents/common/model_config.py`. Never hardcode model strings in individual agent files (except Lesson 2, which is deliberately hardcoded as an intro lesson).

---

## 3. Project Structure

```
adk2_tutorial/                    ← project root
├── .env                          ← API keys, never committed
├── .gitignore                    ← includes .env, .venv, .adk, *.db
├── .python-version               ← pins Python 3.12
├── pyproject.toml
├── config/
│   └── models.yaml               ← central model policy
├── scripts/
│   └── verify_setup.py           ← Lesson 1 setup verification
├── agents/
│   ├── common/                   ← shared utilities, imported by all lessons
│   │   ├── __init__.py
│   │   ├── model_config.py       ← get_model() helper
│   │   ├── finance_tools.py      ← get_stock_price(), get_stock_news() (Tavily)
│   │   ├── runner_utils.py       ← get_or_create_session(), run_agent_query()
│   │   └── callbacks.py          ← reusable callbacks (save_to_memory etc.)
│   ├── lesson02_first_agent/
│   │   ├── __init__.py
│   │   └── agent.py
│   ├── lesson03_loan_tools/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── tools.py
│   ├── lesson04_market_briefing/           ← Claude variant (Tavily)
│   ├── lesson04_market_briefing_gemini_grounded/ ← Gemini variant
│   ├── lesson05_credit_risk/
│   ├── lesson06a_sessions_and_state/
│   │   ├── priority_support/
│   │   │   ├── __init__.py
│   │   │   └── agent.py
│   │   └── main.py
│   ├── lesson06b_sessions_and_state/
│   │   ├── kyc_onboarding/
│   │   └── main.py
│   ├── lesson06c_artifacts/
│   │   ├── loan_report/
│   │   └── main.py
│   ├── lesson07_callbacks_theory/          ← theory only, no agent
│   ├── lesson07a_callbacks/
│   │   ├── wealth_advisor/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── tools.py
│   │   │   └── callbacks.py
│   │   └── main.py
│   ├── lesson07b_long_running_tools/
│   │   ├── credit_check/
│   │   └── main.py
│   ├── lesson08_long_term_memory/
│   │   ├── relationship_manager/
│   │   └── main.py
│   └── lesson09_production_serving/
│       ├── main.py               ← FastAPI server
│       ├── streamlit_app.py
│       └── console_client.py
└── .vscode/
    └── settings.json
```

---

## 4. Lesson Folder Conventions

**From Lesson 6a onward**, lessons use a nested structure with their own `main.py`:
```
agents/lessonNN_topic/
├── agent_name/
│   ├── __init__.py    ← always: from . import agent
│   ├── agent.py       ← agent definition ONLY
│   ├── tools.py       ← tool functions (lesson-local)
│   └── callbacks.py   ← callback functions (lesson-local if domain-specific)
└── main.py            ← drives the lesson
```

`main.py` has two sys.path inserts:
```python
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # adds agents/ for common.*
# Note: uv run adds the script's own directory automatically, making agent_name/ importable
```

**Lessons 2–5** use the flat structure (no nested `main.py`) and run via `adk run` / `adk web`.

**When to use adk run/web vs main.py:**
- Lessons 2–5: `adk run agents/lessonNN_name` or `adk web agents`
- Lessons 6a onward: `uv run agents/lessonNN_topic/main.py`
- If a future lesson uses `adk run`/`adk web` for a specific reason, point it at the agent's subfolder: `adk run agents/lesson07a_callbacks/wealth_advisor`

---

## 5. Code Conventions (All Lessons)

### File organisation
- `agent.py`: Agent declaration only — model, instruction, description, tools list, callback registrations. No business logic.
- `tools.py`: Tool function implementations. One file per agent folder. Lesson-local tools stay here; reusable tools go in `agents/common/`.
- `callbacks.py`: Callback implementations. Domain-specific callbacks stay in the agent folder; generic ones (`save_to_memory`, `log_tool_invocation`) go in `agents/common/callbacks.py`.
- `main.py`: Runner, SessionService, MemoryService, ArtifactService wiring, plus the console loop or demo script.

### Docstrings
Google docstring format throughout. Every tool function needs a docstring with Args and Returns — the model uses the entire docstring as the tool's description.

### File headers
Format:
```python
"""Lesson N: Short description.

Longer explanation.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""
```
Do NOT prefix with "BFSI" — just "Lesson N: ...".

### Tool conventions
- Always return a dict with named fields
- Include `"error"` key for failure cases (ADK telemetry hook)
- If the tool calls an `async` ADK method (e.g. `save_artifact`), the tool must be `async def`
- Wrap in `LongRunningFunctionTool(fn)` for slow operations
- Never use `asyncio.get_event_loop().run_until_complete()` inside a sync tool — make it async instead

### Console input in async loops
Never use bare `input()` inside an `async def`. Always use:
```python
loop = asyncio.get_event_loop()
try:
    user_input = await loop.run_in_executor(None, lambda: input("You: "))
except EOFError:
    break
```
This prevents silent exit when stdin is non-interactive.

### load_dotenv
Every `main.py` must call `load_dotenv(override=True)` before any ADK imports. `override=True` makes `.env` authoritative even if env vars are already set in the shell.

### runner_utils.py (agents/common/)
```python
async def run_agent_query(agent, app_name, user_id, session_id, query,
                           session_service, memory_service=None) -> str:
    session = await get_or_create_session(session_service, app_name, user_id, session_id)
    runner = Runner(app_name=app_name, agent=agent, session_service=session_service,
                    memory_service=memory_service)
    # ... event loop, return final response text
    # Always use session.id (not the raw session_id string) in runner.run_async()
```

### model_config.py (agents/common/)
```python
def get_model(tier: Literal["primary", "escalation", "fallback"] = "primary"):
    # reads config/models.yaml
    # returns AnthropicLlm(model=...) for anthropic provider
    # returns plain string for google provider
```

---

## 6. Lesson Structure Template

Every lesson follows this structure (based on actual lessons written):

```
# Lesson N: Title

[1-2 sentence callback to previous lesson]

## The problem we're solving
[BFSI use case explained — what the problem is, who has it, 
why it matters. Explain problem BEFORE introducing code.]

## [Concept introduction if new — e.g. "Why LLMs need tools at all"]
[Theory section for genuinely new ADK concepts. Use NOTE: callout 
blocks for important caveats or non-obvious behavior.]

## Step 1: [First concrete step]
[Code with folder path clearly shown. After every code listing, 
add explanation paras of what the code does, especially new ADK-
specific code. Don't just show code without explanation.]

## Step N: Run it
[Exact command. Describe what user will see (general, not exact output). 
Give sample prompts to try. Explain what successful output looks like.]

## If you're coming from LangChain or LangGraph
[How this ADK concept maps to LangChain/LangGraph equivalent]

## In this lesson
[Summary of what was covered — always use this exact heading]

## In the next lesson
[Lead with WHAT the next lesson covers, then HOW. 
Never say "Lesson N" by number — say "the next lesson".]
```

**Additional rules:**
- After code listings, always add explanation paragraphs. Never leave a code block unexplained.
- Back-references to previous lessons: use lesson name, not just number. E.g. "from Lesson 6b" not "from earlier."
- "A word on cost" section: add when token usage or cloud cost is materially relevant.
- NOTE callouts: use `> **NOTE:** ...` blockquote format for important caveats.

---

## 7. Standing Instructions (Accumulated from Full Conversation)

**Tone and style:**
- Conversational, like a knowledgeable friend tutoring you — not formal documentation
- Direct, active voice, varied sentence lengths
- No em-dashes. No "not only X but also Y". No metaphors/analogies/clichés.
- No emojis unless reader uses them
- Humanize text — should not sound AI-written
- Address reader as "you/your"

**Content rules:**
- Never introduce a named concept (class, method, object) without explaining what it is the first time
- Never use a tool, class, or method in code before introducing it in prose
- If something was introduced in a previous lesson, a brief reminder is fine — don't assume reader memorized everything
- Challenges and honest caveats are welcomed. If something has a known limitation, say so
- Never claim something works without verifying it actually works (verify code against real ADK source/runtime)

**Code rules:**
- All code must run without errors — verify before including
- Use the latest stable ADK version (2.5.0)
- Complete code listings — never trail off with "..." in the middle of a function
- No hardcoded API keys or secrets in code ever
- Python 3.12 features are fine
- Break large code blocks into small, meaningful functions
- Inline comments for non-obvious lines

**Lesson generation process:**
- Generate one lesson at a time
- Wait for explicit "go ahead" or "next lesson" prompt before generating the next one
- If a lesson has issues, fix before moving on
- When asked to fix something, fix ONLY what was asked — don't regenerate the whole lesson unless asked

**On errors found during development:**
- Reader codes along in real-time. If they report an error, debug it properly — check actual ADK source, don't guess
- If a fix requires changes to a lesson file already generated, regenerate just the relevant section(s) as a str_replace — not the whole lesson

**Diagrams:**
- Use Google color palette: Blue (#4285F4), Green (#34A853), Red (#EA4335), Yellow (#FBBC05), Dark Gray (#3C4043), Black, White
- Minimum font size 14pt for all text in diagrams
- Text inside shapes must wrap properly — never spill over box boundaries
- Use width-aware text wrapping (compute char count from actual box width and font size)
- Compute figure height bottom-up from content — never guess a fixed height
- Red is acceptable but use sparingly
- If diagram quality is poor after 2 attempts, use `[DIAGRAM HERE]` placeholder and suggest reader use Gemini for the image

**LangChain/LangGraph comparisons:**
- Include in every lesson where there's a meaningful parallel
- Always use exact section heading: "If you're coming from LangChain or LangGraph"

**GCP deployment (future lessons):**
- Prefer free tier / cheapest services first
- Every deploy script must have a paired teardown script
- Cloud Run is the preferred compute (cheapest, scales to zero)
- Vertex AI for any Google-specific services (RAG, Agent Engine etc.)
- Flag approximate costs before any lesson that will incur meaningful spend

---

## 8. The Agents/Common Folder — Key Shared Files

### agents/common/model_config.py
Reads `config/models.yaml`, returns correct model object. Used by all lesson agents from Lesson 3 onward.

### agents/common/finance_tools.py
- `get_stock_price(ticker: str) -> dict` — yfinance, supports .NS (India), .DE (Germany), plain (US)
- `get_stock_news(company_or_ticker: str, max_results: int = 5) -> dict` — Tavily search API, requires `TAVILY_API_KEY` in `.env`

### agents/common/runner_utils.py
- `get_or_create_session(session_service, app_name, user_id, session_id)` — fetches or creates
- `run_agent_query(agent, app_name, user_id, session_id, query, session_service, memory_service=None) -> str` — full turn, returns final response text. Uses `session.id` (not raw string) in `runner.run_async`

### agents/common/callbacks.py (created in Lesson 7a)
Generic reusable callbacks. Currently: `save_to_memory` (after_agent_callback).

---

## 9. Key Technical Facts (Verified from ADK 2.5.0 Source)

- `AnthropicLlm(model="...")` is required for Claude — never bare string
- `GoogleSearchTool(bypass_multi_tools_limit=True)` needed to combine google_search with other tools. Still Gemini-only regardless of flag.
- `google_search` singleton: use when search is the only tool. `GoogleSearchTool(bypass_multi_tools_limit=True)`: use when combining with other tools.
- `output_schema` + `tools` on same agent: supported since ADK ~1.17-1.19. Works with Claude via a fallback mechanism (not natively). May occasionally fail on Claude — if model returns plain text instead of schema, this is the cause.
- `output_key="key_name"` on Agent: writes validated output_schema result to session state after every turn automatically.
- Callable instruction: pass a function `(ReadonlyContext) -> str` to `instruction=` parameter.
- `save_artifact` and `load_artifact` on `ToolContext` are async — tool must be `async def`.
- `event.actions.artifact_delta`: dict of {filename: version} for artifacts saved in a turn.
- `InMemoryMemoryService` resets on process exit — both sessions must be in same `main()` call for cross-session memory testing.
- `InMemorySessionService` is pure RAM — not SQLite. `adk run`/`adk web` use their own SQLite-backed service internally, but that's not `InMemorySessionService`.
- Callback parameter names are enforced as keyword args by ADK. Wrong name = TypeError at runtime (not import time).
- `before_model_callback` and `after_model_callback` fire once per model call, not once per turn. With tools, a turn = multiple model calls.
- `gemini-flash-latest` is a rolling alias that can break when Google deprecates the underlying model version. Safe for dev/learning; pin to `gemini-2.5-flash` for production.
- `adk api_server` / `get_fast_api_app()` is production-capable (not just a dev tool like `adk web`). Different from `adk web`.
- `LongRunningFunctionTool`: makes `event.is_final_response()` return True immediately on the function call event. Event loop must collect ALL final-response events in a turn (don't break on first).
- `inject_market_context` / before_model_callback: use `llm_request.append_instructions([...])` to inject — NOT `llm_request.system_instruction` (that attribute doesn't exist).
- `tool_context.state["key"] = value` must reassign the full value — in-place mutation of nested objects doesn't persist.

---

## 10. Packages Added to Project (cumulative)

```bash
uv add google-adk                          # Lesson 1
uv add anthropic python-dotenv pyyaml     # Lesson 1
uv add yfinance                            # Lesson 4
uv add tavily-python                       # Lesson 4 (replaces ddgs)
uv add reportlab                           # Lesson 6c
uv add fastapi uvicorn streamlit requests  # Lesson 9
```

**Note:** No LiteLLM anywhere. `.env` also needs `TAVILY_API_KEY` for Tavily search.

---

## 11. Complete Lesson Sequence

### Completed Lessons (1–10)

| # | Title | Key concept | Run method |
|---|---|---|---|
| 1 | Environment Setup | uv, ADK install, API keys, config | `uv run scripts/verify_setup.py` |
| 2 | Your First Agent | `Agent`, `AnthropicLlm`, `adk run`, `adk web` | `adk run` / `adk web` |
| 3 | Function Tools | `@tool`, `tools.py`, docstring schemas, dict return | `adk run` / `adk web` |
| 4 | Built-in Tools & Grounding | `GoogleSearchTool`, Tavily, Gemini-only limitation | `adk web` |
| 5 | Structured Output + output_key | `output_schema`, Pydantic, `output_key` | `adk web` |
| 6a | Sessions & State: Agent View + callable instruction | `SessionService`, `Session`, `Runner`, pre-seeded state, `main.py` intro | `uv run agents/lesson06a.../main.py` |
| 6b | Sessions & State: Tool View | `ToolContext`, tool-driven state, `{key?}` | `uv run agents/lesson06b.../main.py` |
| 6c | Artifacts | `ArtifactService`, `save_artifact`, `load_artifact`, async tools | `uv run agents/lesson06c.../main.py` |
| 7 | Callbacks — Theory | All 6 callback types, firing order, parameter enforcement | Theory only |
| 7a | Callbacks in Practice | All 6 callbacks on wealth advisor agent, `callbacks.py` split | `uv run agents/lesson07a.../main.py` |
| 7b | Long-Running Tools | `LongRunningFunctionTool`, async event collection | `uv run agents/lesson07b.../main.py` |
| 8 | Long-Term Memory | `MemoryService`, `load_memory`, `add_session_to_memory` | `uv run agents/lesson08.../main.py` |
| 9 | Production Serving | FastAPI, `runner_utils.py`, Streamlit, console client | `uv run agents/lesson09.../main.py` |
| 10 | Anatomy of an Agent | Full single-agent recap (theory only) | Theory only |

### Upcoming Lessons (11 onward)

| # | Title | Key Concept |
|---|---|---|
| 11 | Multi-Agent Theory | `SequentialAgent`, `ParallelAgent`, `LoopAgent` — theory only, no code |
| 11a | SequentialAgent in Practice | Loan underwriting pipeline — credit → risk → decision |
| 11b | ParallelAgent in Practice | Parallel risk checks feeding into sequential decisioning |
| 11c | LoopAgent in Practice | Iterative review loop combining with Sequential/Parallel |
| 12 | Human-in-the-Loop | Pausing pipelines for human approval — loan officer sign-off |
| 13 | Skills — Packaging and Reusing Agent Capabilities | Reusable skill bundles; back-references 11a/11b/11c |
| 14 | MCP Servers | `McpToolset`, building your own MCP server — mutual fund/NAV data |
| 15 | Agent-to-Agent Delegation | `AgentTool` (in-process) then A2A cross-service — fraud → compliance |
| 16 | Graph-Based Workflows | ADK 2.0 `Workflow`, routing, fan-out/fan-in, graph-based HITL |
| 17 | Guardrails & Agent Evaluation | `Plugin`, ADK eval framework — wealth management compliance |
| 18 | Capstone: BFSI Advisory Platform | End-to-end personal finance advisor — full integration |
| 19 | Deploying to GCP | Cloud Run (free tier first), paired deploy + teardown scripts |

**All lessons 11+ use `uv run .../main.py` as the run method. No Opus model anywhere.**

**Lesson 11 (Theory only):** Pure theory. Covers what SequentialAgent, ParallelAgent, and LoopAgent are, when to use each, and how they compose. No code — sets up 11a/11b/11c.

**Lesson 11a (SequentialAgent):** Loan underwriting pipeline. Specialist agents: CreditAgent → RiskAgent → DecisionAgent, wired in a SequentialAgent. Each specialist has its own `agent.py`, `tools.py` in a `sub_agents/` subfolder under the orchestrator. Uses `output_schema` so each agent produces structured output the next one can consume.

**Lesson 11b (ParallelAgent):** Multiple specialist agents (credit risk, market risk, compliance check) run simultaneously via ParallelAgent, results aggregated by a sequential decisioning step. Shows how to combine ParallelAgent inside a SequentialAgent pipeline.

**Lesson 11c (LoopAgent):** Iterative review loop. A LoopAgent that keeps refining an assessment until a quality threshold is met or a condition signals done. Combines with Sequential/Parallel from prior lessons. Demonstrates exit conditions.

**Lesson 12 (HITL — Human-in-the-Loop):** Full BFSI example — retail bank loan approval pipeline with officer sign-off:
- CreditAgent → RiskAgent → HITL Checkpoint → DisbursementAgent (if APPROVED) or ReferralAgent (if REFERRED)
- HITL implemented as `HumanApprovalTool`: displays findings from session state, prompts officer for APPROVE/REJECT/REFER, writes decision back to session state, uses `run_in_executor` for blocking input
- If APPROVED: DisbursementAgent generates loan offer letter PDF as an artifact (uses Lesson 6c pattern)
- If REFERRED: ReferralAgent generates follow-up task with reasons
- "What this looks like in production" section: tool writes to DB, REST endpoint surfaces to officer dashboard, webhook resumes pipeline — agent code unchanged
- Points forward to Lesson 16 where graph-based HITL handles this more elegantly with explicit approval nodes

**Lesson 13 (Skills):** Looks back at 11a/11b/11c and shows how repeated tools (credit scoring, DTI calculation) duplicated across specialist agents can be packaged into a reusable `CreditIntelligenceSkill`. Skill lives in `agents/common/skills/`. Shows the same skill imported by two different agents with zero duplication. Maps to LangChain's `Toolkit`.

**Lesson 14 (MCP):** `McpToolset` for consuming external MCP servers. Builds own MCP server for mutual fund/NAV data. MCP tools appear identical to function tools from the agent's perspective.

**Lesson 15 (A2A):** Two parts — (1) `AgentTool` wrapping one agent as a tool for another (in-process, same `main.py`), (2) True A2A cross-service: two separate FastAPI servers communicating via ADK Task API — fraud detection agent delegates to compliance agent running as a separate service.

**Lesson 16 (Graph-Based Workflows):** ADK 2.0 `Workflow` runtime. Explicit routing nodes, fan-out/fan-in, conditional branching. Graph-based HITL with approval nodes (cleaner than Lesson 12's callback approach). Loan origination end-to-end.

**Lesson 17 (Guardrails & Evaluation):** `Plugin` interface. ADK's built-in eval framework. Writing eval datasets. Running evaluations. Compliance guardrails for wealth management.

**Lesson 18 (Capstone):** End-to-end BFSI advisory platform integrating multi-agent orchestration, skills, memory, callbacks, artifacts, HITL, and production serving. Full system, not isolated demos.

**Lesson 19 (GCP Deployment):**
- Cloud Run for the FastAPI agent server (scales to zero = free when idle)
- Vertex AI RAG for production MemoryService (replaces InMemoryMemoryService)
- Artifact Registry for container images
- Secret Manager for API keys (replaces .env)
- Always pair every deploy script with a teardown script
- Flag approximate costs upfront before any step that incurs spend
- Free tier first throughout

**Multi-agent folder structure (Lessons 11+):**
```
agents/lesson11a_sequential_agent/
├── main.py
└── loan_underwriting/                ← orchestrator
    ├── __init__.py
    ├── agent.py                      ← imports and wires sub-agents
    ├── tools.py
    ├── callbacks.py
    └── sub_agents/                   ← flat, not nested inside each other
        ├── __init__.py
        ├── credit_agent/
        │   ├── __init__.py
        │   ├── agent.py
        │   └── tools.py
        ├── risk_agent/
        │   ├── __init__.py
        │   ├── agent.py
        │   └── tools.py
        └── decision_agent/
            ├── __init__.py
            ├── agent.py
            └── tools.py
```
Sub-agents are in-process Python objects, NOT separate API servers.
Exception: Lesson 15 (A2A) second half uses two separate lesson folders each with their own FastAPI server.


---

## 12. Uploaded Lesson Files (Ground Truth)

The following lesson files were uploaded by the reader as their offline-edited final versions. These are the authoritative source for what each lesson contains — not anything generated in a prior chat session:

- Lesson-01-Environment-Setup.md
- Lesson-02-Your-First-Agent.md
- Lesson-03-Function-Tools.md
- Lesson-04-Built-in-Tools.md
- Lesson-05-Structured-Output.md
- Lesson-06a-Sessions-and-State-Agent-View.md
- Lesson-06b-Sessions-and-State-Tool-View.md
- Lesson-06c-Artifacts.md
- Lesson-07-Callbacks.md
- Lesson-07a-Callbacks-in-Practice.md
- Lesson-07b-Long-Running-Tools.md
- Lesson-08-Long-Term-Memory.md
- Lesson-09-Production-Serving.md
- Lesson-10-Anatomy-of-an-Agent.md

When a new lesson references a previous one, refer to these files as the definitive content. If a reader uploads a lesson file in a future session, treat the uploaded version as the authoritative source over any version generated in that session.
