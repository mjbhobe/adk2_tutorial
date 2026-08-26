# Continuation Prompt: GCP Deployment, Then BFSI Capstones

I've attached the series bible for this project. Read it first. It covers everything from Lessons 1 through 15a, all standing conventions, and the shared `agents/common/` code you should keep reusing. Workflows do not exist in this chat, don't reference them.

**Generate one piece at a time.** One deployment example in Phase 1, one capstone in Phase 2. Wait for an explicit go-ahead before moving to the next one. Do not generate the next item just because the previous one is done. This applies across both phases, the same discipline this whole series has used from Lesson 1 onward.

Both phases are already scoped and agreed below. Don't re-propose them, build them as described. If something turns out to be genuinely wrong or infeasible once you're actually building it, say so plainly and we'll adjust, the same way this series has always handled a plan meeting reality.

---

## Phase 1: Deploying Agentic AI Apps to GCP

A standalone, general guide to deploying an ADK agent to Google Cloud. Not tied to one capstone, this is reusable methodology Phase 2 will lean on directly.

**Requirements, all real constraints, not preferences:**

- No GCP free trial credit. Every cost is real, out of pocket. Default assumption throughout.
- Cover the real deployment options for an ADK agent, Cloud Run, Agent Engine, GKE at minimum. Compare honestly, cost, complexity, when each one actually makes sense. Then recommend the cheapest viable option for the hands-on examples below, unless there's a real reason not to.
- Everything script driven. Deploy, test, and tear down from the CLI, not the console.
- Teardown must be genuinely clean, every service stopped and deleted, nothing left billing. I want to repeat the full cycle multiple times without worrying about leftover charges.
- No long-running test jobs. Nothing that racks up cloud time or API spend just to prove it works.
- State approximate costs before any step that spends real money, every time, not just once.

**The four examples, in order, simple to advanced, all reusing code already built and verified in this series, no new code written for this guide:**

1. **Lesson 2**, the simplest possible single agent. The first deploy-and-teardown rehearsal.
2. **Lesson 11a**, a real `SequentialAgent` pipeline. Still one service, a genuine step up.
3. **Lesson 9**, already has FastAPI and Streamlit built. The closest existing lesson to a real deployable web app's shape.
4. **Lesson 15a**, the A2A pair. Two real services that need to reach each other over an actual network, not localhost. The hardest case, and deliberately the last one, since Phase 2's fourth capstone will reuse whatever gets worked out here.

---

## Phase 2: BFSI Capstones, Lessons 1 Through 15 Only

Four capstones, simple to medium complexity, business-user relevant, no `Workflow` class anywhere. Already scoped:

1. **Personal Wealth Advisor.** Single agent core, structured output, sessions and state, artifacts (a real PDF report), long-term memory, a callback or two. Real data, `yfinance` and `api.mfapi.in`. One Cloud Run service, the simplest of the four.

2. **Loan Origination Pipeline.** `SequentialAgent` for the pipeline, `ParallelAgent` for concurrent checks, `AgentTool` for a specialist sub-task, and real Human-in-the-Loop, a loan officer's own decision genuinely pauses and resumes the pipeline. One Cloud Run service. The interesting problem here is translating console-based approval into a real Streamlit "pending approval" screen.

3. **Mutual Fund Research Assistant.** Skills, a glossary skill and a calculation skill, plus MCP, reusing and extending the real mutual fund server from `14b`. Real Indian and global fund data throughout. One Cloud Run service, the MCP server runs as a subprocess inside it, `stdio`, not a second deployed service.

4. **Cross-Team Risk Assessment.** A2A, serving and consuming, reusing and extending `risk_specialist_agent` from `15a`. Show the same capability two ways, once as an in-process `AgentTool` call, once as a genuine cross-service A2A call, side by side. Two real Cloud Run services, reusing the deployment pattern already worked out in Phase 1's fourth example.

**Requirements for every capstone:**

- Free libraries and free data sources throughout. Where real free data genuinely isn't available, say so plainly and use clearly labeled synthetic data instead.
- Runs locally first, then deploys to GCP using Phase 1's methodology. Both paths need to actually work.
- Its own GCP setup, deploy, test, and teardown steps, same discipline as Phase 1.
- Real test cases, concrete inputs, and what the reader should actually see back.
- A Streamlit front end. Real input in, real output out.
- A visible spinner for anything that takes real time.
- Where an agent's own intermediate reasoning or tool calls are worth showing, log them into a collapsible section on the front end, and collapse it automatically once the final answer is ready.

---

Start with Phase 1, example 1. Confirm you've read the bible, then begin.
