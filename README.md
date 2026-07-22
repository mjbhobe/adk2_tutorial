# Building Agents with the Google ADK 2.x - A tutorial series 

## What is Google ADK?

Google's Agent Development Kit (ADK) is an open-source, code-first Python framework for building, evaluating, and deploying AI agents. Google introduced it in April 2025 and open-sourced it shortly after. It reached general availability at version 2.0 in May 2026, and it now ships in five languages: Python, TypeScript, Go, Java, and Kotlin.

At its core, ADK gives you two building blocks. An `Agent` defines what a single AI does: its instructions, the model behind it, and the tools it can call. A `Workflow` orchestrates multiple agents and tasks together, using a graph you define explicitly, with support for routing, branching, retries, and human approval steps along the way. Everything else in the framework (sessions, memory, structured output, tool integrations) exists to support those two ideas.

## What can you build with it?

By the time you finish this series, you'll have used ADK for:

- **Tool-calling agents** that do real work: run calculations, hit APIs, query data.
- **Structured output**, where an agent's response is guaranteed to match a schema you define, not just prose you hope parses correctly.
- **Multi-turn conversations with memory**, both within a session and across separate sessions days apart.
- **Multi-agent orchestration**, where several specialized agents collaborate on one task, either through fixed sequences and parallel branches, or through a full graph-based workflow with conditional routing.
- **MCP (Model Context Protocol) integration**, connecting agents to external tools and data sources through a standard interface, including building your own MCP server.
- **A2A (Agent-to-Agent) communication**, where one agent delegates work to another as a structured task, potentially across different frameworks or vendors entirely.
- **Deployment**, taking an agent from your laptop to a live Google Cloud service, cheaply.

Almost all the examples we build in this series will be focused on the BFSI domain.

## Why use ADK, specifically?

A few things make it worth learning, beyond "Google built it":

**It's genuinely model-agnostic, not just in theory.** Yes, it's optimized for Gemini, and Gemini is the only option for a couple of built-in tools like Search grounding. But the core framework works the same way regardless of which model sits behind your agent, and we're going to prove that by defaulting to Claude for almost everything in this series.

**Graph-based workflows, without losing the simple path.** ADK 2.0's biggest addition is a deterministic, graph-based execution engine for composing agent workflows, complete with fan-out/fan-in, loops, retries, and human-in-the-loop steps. Crucially, this sits alongside the simpler `SequentialAgent` / `ParallelAgent` / `LoopAgent` classes from ADK 1.x, which still work and are often the right tool for a straightforward pipeline. You get to choose the right level of complexity for the problem in front of you, and we'll cover both the approaches.

**MCP and A2A are first-class, not bolted on.** MCP handles the "vertical" problem: connecting one agent to tools and data. A2A handles the "horizontal" problem: agents from different systems, possibly built by different teams or vendors, discovering and delegating to each other through a structured protocol. Both are core to ADK 2.0's Task API, and we'll build with both.

**It has an actual evaluation framework built in.** Not every agent framework does. ADK ships tooling to test agent behavior before you deploy it, which matters more than it sounds like the first time an agent quietly starts behaving differently after a prompt tweak.

## How does it compare to LangChain / LangGraph and CrewAI?

You already know LangChain and LangGraph, so here's the honest comparison rather than a marketing one, since all three of these are legitimate, production-used tools with different design centers.

| | **Google ADK** | **LangGraph** | **CrewAI** |
|---|---|---|---|
| **Core abstraction** | Agents and graph-based workflows, with an event-driven runtime managing state between LLM calls and tool executions | A directed graph of nodes with explicit edges you define; you control exactly how state flows and where errors route | "Crews": groups of role-based agents (a goal, a role, a set of tools) collaborating on a shared task |
| **Where it shines** | Deterministic, auditable multi-step pipelines; teams already on Google Cloud; needing both MCP (tools) and A2A (cross-framework agent delegation) natively | Maximum control over complex, branching, stateful workflows; you're comfortable owning more of the wiring yourself | Fastest path from zero to a working multi-agent demo; simplest mental model for a first multi-agent system |
| **Production track record** | Newest of the three; GA as of May 2026, smaller community, documentation still maturing in places | The most battle-tested for complex production systems today; Klarna reportedly runs it at 85 million users | Strong for prototyping and internal automation; less commonly the final production layer for complex branching logic |
| **Structured workflows** | Native graph runtime (2.0) plus simpler sequential/parallel/loop agent classes for straightforward cases | Native and mature; this is LangGraph's original reason for existing | Process types (sequential, hierarchical) rather than a general graph; less granular control over conditional branching |
| **Cross-framework agent communication** | Native A2A protocol support, designed specifically so ADK agents can delegate to agents built on other frameworks entirely | Not a first-class concept; you'd build this yourself | Not a first-class concept |
| **Language support** | Python, TypeScript, Go, Java, Kotlin | Python, TypeScript | Python |

If you're coming from LangGraph specifically: the mental model translates reasonably well once you reach ADK 2.0's `Workflow` class, since both frameworks eventually converged on graph-based orchestration with explicit edges. Where they genuinely differ is scope. LangGraph gives you the graph and expects you to build most of the surrounding infrastructure (tool integration patterns, deployment, evaluation) yourself or via the wider LangChain ecosystem. ADK bundles more of that in the box: sessions, memory services, an evaluation framework, MCP and A2A support, and a defined path to Cloud Run or Vertex AI deployment, all under one framework. That's a real trade-off, not a strictly better one: you gain a more complete out-of-the-box toolkit, and you give up some of the fine-grained control and ecosystem maturity LangGraph has built up over a longer production history.

We'll call out specific LangChain/LangGraph parallels throughout the series wherever a concept maps closely, since that's the fastest way for you to build real intuition rather than starting from zero.

## How this series works

Every lesson is a self-contained,  tutorial: full project setup, complete code for every file (nothing hardcoded that should be config), and instructions to run it locally with `adk run`, `adk web`, or `uv run main.py`, depending on what fits the lesson. From Lesson 3 onward, every example is a real BFSI (Banking, Financial Services, and Insurance) application, not a toy. We're building things like loan underwriting pipelines, credit risk scorers, KYC onboarding flows, and investment research agents, using free public data sources like `yfinance` for market data.

On models: Claude Haiku is the default for nearly everything, since it's the cheapest capable option and keeps this series affordable to actually follow along with. We escalate to Claude Sonnet only where a lesson genuinely needs stronger reasoning, and I'll say so explicitly when that happens. Gemini Flash appears in exactly one lesson, where ADK's built-in Google Search grounding tool requires a Gemini model by design. Claude Opus is never required anywhere in this series.

## The lesson outline

| # | Lesson | What you build | Core ADK concept |
|---|--------|----------------|-------------------|
| 1 | [Setting Up Your ADK Environment](blogs/Lesson-01-Environment-Setup.md) | `uv` project scaffold, ADK install, Claude and Gemini Flash keys wired up, VS Code configured | Project structure, environment verification |
| 2 | [Your First Agent](blogs/Lesson-02-Your-First-Agent.md) | A minimal greeting agent (the last non-BFSI example in the series) | `LlmAgent`, `adk run`, `adk web` |
| 3 | [Function Tools](blogs/Lesson-03-Function-Tools.md) | Loan EMI and affordability calculator agent | `@tool`-style function tools, `ToolContext` |
| 4 | Built-in Tools & Grounding | Market briefing agent pulling live prices via `yfinance` plus Google Search grounding | Built-in tools, tool mixing, the Gemini-only grounding limitation |
| 5 | Structured Output | Credit risk scoring agent that always returns a validated JSON verdict | `output_schema`, Pydantic, `output_key` |
| 6 | Sessions & State | Multi-turn KYC (Know Your Customer) onboarding agent that remembers what's been collected | `Session`, `SessionService`, `state` |
| 7 | Long-Term Memory | Relationship manager assistant that recalls a client's preferences across separate sessions | `MemoryService`, `load_memory` tool |
| 8 | Classic Multi-Agent Workflows | Loan underwriting pipeline: parallel risk checks, sequential decisioning, loop-based re-review | `SequentialAgent`, `ParallelAgent`, `LoopAgent` |
| 9 | MCP Servers | Custom MCP server exposing mutual fund and NAV data, consumed by an investment research agent | `McpToolset`, building your own MCP server |
| 10 | Agent-to-Agent Delegation | Fraud alert agent that delegates a case to a separate compliance-review agent | Task API, `AgentTool`, delegation patterns |
| 11 | Graph-Based Workflows | Full loan origination flow with branching, fan-out/fan-in, retries, and human-in-the-loop approval | ADK 2.0 `Workflow`, routing, HITL |
| 12 | Guardrails, Callbacks & Eval | Wealth management assistant with compliance guardrails and automated evaluation | Callbacks, `Plugin`, ADK evaluation framework |
| 13 | Capstone: BFSI Advisory Platform | End-to-end personal finance advisor combining tools, memory, multi-agent orchestration, and MCP | Full integration, `uv run main.py` |
| 14 | Deploying to GCP | Deploy the capstone to Cloud Run on the free tier, with a paired teardown script | GCP deployment, cost control |

## What you'll be able to do by the end

By Lesson 14, you'll be able to design and ship a working, production-shaped ADK agent system from scratch: one that calls real tools, holds structured conversations across sessions, remembers things about the people it talks to, coordinates multiple specialized agents on a single task (through both simple pipelines and full graph-based workflows), pulls in external data and tools through MCP, delegates work to other agents through A2A, and enforces compliance-style guardrails before anything reaches a user. You'll have done all of it against real BFSI problems, not toy examples, and you'll know exactly how it costs, both in LLM tokens and in Google Cloud spend, and how to tear the cloud side back down to zero when you're done testing.

You'll also come out of it with a working sense of when ADK is the right call versus LangGraph or CrewAI, since you'll have built the same category of problem (multi-agent orchestration, structured output, tool use) enough times to feel the difference in your hands, not just read about it in a table.

Hope you enjoy learning ADK as much as I enjoyed developing this series.