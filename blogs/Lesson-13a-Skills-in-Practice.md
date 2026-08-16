# Lesson 13a: Skills in Practice

A `Skill` packages knowledge or procedure, not code an agent always carries, so it can be discovered and pulled in only when actually relevant, rather than bloating every agent's instruction with guidance most conversations never touch. You reach for one when a capability is genuinely optional per conversation, checking a PAN, calculating an EMI, something an agent shouldn't need to know about by default but should be able to find and use the moment it's needed.

Quick recap: a Skill is a `SKILL.md` file, required `name` and `description`, an optional instructions body, and optional `references/`, `assets/`, and `scripts/` folders, loaded in layers so an agent only pays for what it actually decides to use. `SkillToolset` gives an agent four tools of its own, list, load, load a resource, run a script, and the model decides when to reach for each. The theory lesson also confirmed something worth actually seeing work, not just reading about: a Skill, a plain function tool, and an `AgentTool` can all sit on the same agent at once, resolved together with no special handling. This lesson builds three skills, from the simplest possible shape up to a scripted one, plus that full combination, for real.

## The problem we're solving

The loan support desk needs three different kinds of capability, and they don't all belong in the same place.

**Procedure**: explaining what a loan term means, checking a PAN and pulling a credit report, or calculating an exact EMI, needs no dedicated agent of its own, just guidance, sometimes a tool, sometimes a real script. That's what Skills are for.

**Judgment**: a full risk assessment, credit score plus affordability plus default history combined into a score and a band, is a heavier task than a quick lookup, worth its own dedicated agent turn with its own instruction. That's what `AgentTool` is for.

**Something always needed, regardless of the other two**: every customer interaction gets logged for compliance, whether it touched a skill, the risk specialist, both, or neither. That's a plain tool, sitting directly in the agent's own list, not gated behind anything.

One demo agent, five pieces: `loan-terms-glossary` (a skill with nothing but instructions, no tools at all), `pan-credit-check` (a skill that does gate tools), `emi-calculator` (a scripted skill), `risk_specialist_agent` (`AgentTool`), and `record_customer_query` (always-on plain tool).

## Step 1: Set up the folder structure

```
agents/lesson13a_skills/
├── main.py
└── skills_demo/
    ├── __init__.py
    ├── agent.py
    ├── credit_tools.py
    ├── support_tools.py
    ├── risk_specialist/
    │   ├── __init__.py
    │   ├── agent.py
    │   └── tools.py
    └── skills/
        ├── loan-terms-glossary/
        │   └── SKILL.md
        ├── pan-credit-check/
        │   └── SKILL.md
        └── emi-calculator/
            ├── SKILL.md
            └── scripts/
                └── calculate_emi.py
```

Two things worth noticing before you build this. `credit_tools.py` sits at the `skills_demo/` level, not inside `pan-credit-check/`. That's deliberate: skill folders use kebab-case, the naming convention ADK's Skills format expects, and `pan-credit-check` isn't valid as a Python package name, you can't `import` a folder with a hyphen in it. A tool a skill wants to activate still has to be real, importable Python code, so it lives in your normal module structure, and the skill's frontmatter just references it by name. And `skills/` itself has no `__init__.py`, it's never imported as Python, `load_skill_from_dir` just reads it off disk as a plain filesystem path.

`risk_specialist/` is its own small agent folder, the same shape you've used since Lesson 11a, since it's going to be wrapped in an `AgentTool` rather than loaded as a skill.

## Step 2: Build the simplest possible skill

Before anything with tools, here's the simplest shape this format can take, nothing but instructions:

```markdown
---
name: loan-terms-glossary
description: |
  Explains common loan and banking terms in plain language for
  customers who don't recognize financial jargon. Use this whenever a
  customer asks what a term means, EMI, NAV, moratorium, and similar.
---

# Loan Terms Glossary

When a customer asks what a term means, explain it in plain, simple
language, no jargon in the explanation itself. Common terms:

- **EMI (Equated Monthly Installment)**: the fixed amount paid every
  month toward a loan, covering both interest and part of the principal.
- **NAV (Net Asset Value)**: the price of one unit of a mutual fund,
  updated once a day based on the fund's holdings.
- **Moratorium**: a period during which the borrower isn't required to
  make loan payments, interest may still accrue.
- **Processing fee**: a one-time charge a lender takes to process a
  loan application, deducted from the loan amount or paid upfront.
- **Prepayment**: paying off part or all of a loan before its
  scheduled end date, sometimes with an extra charge.

If asked about a term not listed here, explain it using your own
general knowledge, staying in plain language.
```

Save this as `skills_demo/skills/loan-terms-glossary/SKILL.md`. No `metadata`, no `adk_additional_tools`, no `scripts/`. Nothing gets unlocked when this loads, checking the agent's available tools before and after loading it shows an identical list, confirmed directly. All that changes is what the model has read, its own reasoning improves, nothing about what it can *do* does.

Worth being upfront about what that means for checking this specific example, differently from every other one in this lesson. There's no deterministic return value here, no NAV, no risk score, nothing a tool computed that you can confirm against a known-correct number. Verifying this skill means confirming it loads and activates correctly, which you can check directly, not confirming a specific "correct" answer, since no tool is producing one.

## Step 3: Build the tools behind the instructions-only skill

Create `agents/lesson13a_skills/skills_demo/credit_tools.py`

```python
"""Lesson 13a: Plain Python tools, activated by the pan-credit-check skill.
"""

import hashlib
import re

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def validate_pan_format(pan_number: str) -> dict:
    """Validates that a string matches the Indian PAN (Permanent Account Number) format.

    Same check used throughout this series: 5 uppercase letters, 4
    digits, 1 uppercase letter.

    Args:
        pan_number: The PAN string to validate.

    Returns:
        A dict with:
            valid (bool): True if the format matches, False otherwise.
            pan_number (str): The PAN as received, uppercased and stripped.
            error (str, optional): Present only when valid is False.
    """
    cleaned = pan_number.strip().upper()
    if PAN_PATTERN.match(cleaned):
        return {"valid": True, "pan_number": cleaned}
    return {
        "valid": False,
        "pan_number": cleaned,
        "error": f"'{cleaned}' does not match the PAN format (5 letters, 4 digits, 1 letter).",
    }


def get_credit_bureau_report(pan_number: str) -> dict:
    """Fetches a mock credit bureau report for an applicant.

    Same deterministic mock mechanism used throughout this series: a
    hash of the PAN, so the same applicant always gets the same result.

    Args:
        pan_number: The applicant's validated PAN number.

    Returns:
        A dict with:
            pan_number (str): The PAN the report was generated for.
            credit_score (int): A CIBIL-style score between 300 and 900.
            existing_loans_count (int): Number of currently active loans.
            has_defaults (bool): True if the mock history includes a default.
    """
    digest = hashlib.sha256(pan_number.encode()).hexdigest()
    seed = int(digest[:8], 16)
    return {
        "pan_number": pan_number,
        "credit_score": 300 + (seed % 601),
        "existing_loans_count": seed % 4,
        "has_defaults": (seed % 7) == 0,
    }
```

Nothing new here, this is the same PAN check and credit bureau mock from 11a and 12. What's new is how it gets connected to the agent, which happens two steps from now, not through the agent's own `tools=[]` list directly.

## Step 4: Write the instructions-only skill that gates tools

Create `skills_demo/skills/pan-credit-check/SKILL.md`.

```markdown
---
name: pan-credit-check
description: |
  Validates an Indian PAN (Permanent Account Number) and fetches a mock
  credit bureau report for that PAN. Use this whenever an agent needs
  to check a PAN's format or look up an applicant's credit history.
metadata:
  adk_additional_tools:
    - validate_pan_format
    - get_credit_bureau_report
---

# PAN & Credit Check

A PAN (Permanent Account Number) is India's tax ID, and the standard
identity check for a financial application. A valid PAN is exactly 10
characters: 5 uppercase letters, 4 digits, 1 uppercase letter, for
example ABCDE1234F.

When you need to check or use a PAN:

1. Call `validate_pan_format` with the PAN as given. Never judge the
   format yourself, always call the tool.
2. If it's valid, and you also need the applicant's credit history,
   call `get_credit_bureau_report` with the same PAN.
3. If the format check fails, tell the caller the PAN is invalid and
   why, don't attempt a credit check on an invalid PAN.

Both tools return deterministic mock data for this lesson, the same
result every time for a given PAN, standing in for a real government
PAN registry and a real credit bureau.
```

The `metadata.adk_additional_tools` list is what actually connects this skill to the two functions from Step 3, it names them, it doesn't define them, the real Python functions get supplied separately when the agent's `SkillToolset` is built, in Step 7.

## Step 5: Build the scripted skill

Worth admitting upfront: EMI calculation doesn't strictly need to be a scripted skill, it's chosen here purely to illustrate this other way of building one, not because EMI specifically demands it. Lesson 13 covers when a scripted skill actually earns its place over a plain function tool, and how common that really is in practice, this lesson is just the build.

Create `agents/lesson13a_skills/skills_demo/skills/emi-calculator/scripts/calculate_emi.py`

```python
#!/usr/bin/env python3
"""Lesson 13a: EMI calculator, run directly by the emi-calculator skill.

This runs as a real subprocess when run_skill_script executes it, not
as a Python function called in-process, so it takes plain command-line
arguments and prints its result to stdout, exactly like any standalone
CLI script would.
"""

import argparse
import json


def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Calculates the standard amortized EMI for a loan.

    Same reducing-balance formula used throughout this series.

    Args:
        principal: Loan amount, in INR.
        annual_rate: Annual interest rate, as a percentage.
        tenure_months: Loan tenure, in months.

    Returns:
        The monthly EMI, in INR.
    """
    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        return principal / tenure_months
    growth_factor = (1 + monthly_rate) ** tenure_months
    return principal * monthly_rate * growth_factor / (growth_factor - 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate a loan's exact monthly EMI.")
    parser.add_argument("--principal", type=float, required=True, help="Loan amount, in INR")
    parser.add_argument("--annual-rate", type=float, required=True, help="Annual interest rate, as a percentage")
    parser.add_argument("--tenure-months", type=int, required=True, help="Loan tenure, in months")
    args = parser.parse_args()

    emi = calculate_emi(args.principal, args.annual_rate, args.tenure_months)

    print(json.dumps({
        "principal": args.principal,
        "annual_rate": args.annual_rate,
        "tenure_months": args.tenure_months,
        "emi": round(emi, 2),
    }))


if __name__ == "__main__":
    main()
```

This is a plain, standalone CLI script, `argparse` and all. `run_skill_script` runs it more or less exactly the way you'd run it from a terminal yourself, the model supplies `--principal`, `--annual-rate`, and `--tenure-months` as what ADK calls long options, and the script's own stdout, that one line of JSON, is what comes back as the result.

Now the skill that documents it:

Create `skills_demo/skills/emi-calculator/SKILL.md`

```markdown
---
name: emi-calculator
description: |
  Calculates the exact monthly EMI (equated monthly installment) for a
  loan, given the principal, annual interest rate, and tenure in
  months. Use this whenever a precise EMI figure is needed rather than
  an estimate.
---

# EMI Calculator

Never estimate an EMI yourself, run the calculator script instead.

Call `run_skill_script` with:
- `skill_name`: "emi-calculator"
- `file_path`: "scripts/calculate_emi.py"
- `args`: an object with `principal`, `annual-rate`, and `tenure-months`,
  matching the loan's amount (INR), annual interest rate (percentage),
  and tenure (months)

For example, for a loan of 500000 at 10.5% over 36 months:
`args={"principal": "500000", "annual-rate": "10.5", "tenure-months": "36"}`

The script prints a JSON object to stdout with the calculated `emi`.
Read the EMI from that output, don't recompute it yourself.
```

Unlike `pan-credit-check`, there's no `metadata.adk_additional_tools` here, this skill doesn't activate any pre-written function, it tells the model how to invoke its own bundled script through `run_skill_script`.

## Step 6: Build the risk specialist and the always-on logging tool

The risk specialist is a small agent, the same shape as any single-purpose agent since Lesson 11a, not a skill:

Create `agents/lesson13a_skills/skills_demo/risk_specialist/tools.py`

```python
"""Lesson 13a: Tools for the risk specialist agent.
"""


def calculate_emi(loan_amount: float, annual_rate: float, tenure_months: int) -> float:
    """Calculates the standard amortized EMI for a loan.

    Same reducing-balance formula used throughout this series.

    Args:
        loan_amount: Principal amount, in INR.
        annual_rate: Annual interest rate, as a percentage.
        tenure_months: Loan tenure, in months.

    Returns:
        The monthly EMI, in INR.
    """
    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        return loan_amount / tenure_months
    growth_factor = (1 + monthly_rate) ** tenure_months
    return loan_amount * monthly_rate * growth_factor / (growth_factor - 1)


def calculate_risk_score(
    credit_score: int,
    annual_income: float,
    loan_amount: float,
    tenure_months: int,
    has_defaults: bool,
) -> dict:
    """Calculates a deterministic risk score for a loan application.

    Same formula shape as Lesson 11a and 12: up to 60 points from the
    credit score, up to 40 from affordability, minus a 25-point penalty
    for a prior default. Uses a flat 10.5% assumed rate for the
    affordability check, matching Lesson 12's risk agent.

    Args:
        credit_score: CIBIL-style score between 300 and 900.
        annual_income: Applicant's declared annual income, in INR.
        loan_amount: Requested loan amount, in INR.
        tenure_months: Requested tenure, in months.
        has_defaults: Whether the credit report shows a prior default.

    Returns:
        A dict with:
            risk_score (float): 0 to 100, higher means lower risk.
            risk_band (str): "Low", "Medium", or "High".
            emi_to_income_ratio (float): EMI as a fraction of monthly income.
    """
    credit_component = (credit_score / 900) * 60

    monthly_income = annual_income / 12
    emi = calculate_emi(loan_amount, 10.5, tenure_months)
    emi_to_income_ratio = round(emi / monthly_income, 2)
    affordability_component = max(0.0, (1 - emi_to_income_ratio) * 40)

    risk_score = credit_component + affordability_component
    if has_defaults:
        risk_score -= 25

    risk_score = round(max(0.0, min(100.0, risk_score)), 1)

    if risk_score >= 70:
        risk_band = "Low"
    elif risk_score >= 45:
        risk_band = "Medium"
    else:
        risk_band = "High"

    return {
        "risk_score": risk_score,
        "risk_band": risk_band,
        "emi_to_income_ratio": emi_to_income_ratio,
    }
```

Create `agents/lesson13a_skills/skills_demo/risk_specialist/agent.py`

```python
"""Lesson 13a: Risk specialist agent, wrapped as an AgentTool.

A judgment task, not a quick lookup, worth its own dedicated agent
turn rather than a skill an orchestrator loads for a few seconds.
"""

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

The always-on tool is much simpler, deliberately, since its whole point is that it's not gated behind anything:

Create `agents/lesson13a_skills/skills_demo/support_tools.py`

```python
"""Lesson 13a: An always-available tool, not gated behind any skill.
"""

import hashlib


def record_customer_query(query_summary: str, category: str) -> dict:
    """Logs a customer interaction for compliance and audit purposes.

    Every customer interaction gets logged, regardless of which skill,
    if any, handled it. That's exactly why this is a plain tool sitting
    directly in the agent's own tools list, not something gated behind
    a skill's activation state.

    Args:
        query_summary: A short summary of what the customer asked.
        category: One of "pan_credit", "emi", "risk", or "general".

    Returns:
        A dict with:
            logged (bool): Always True in this mock.
            reference_id (str): A mock audit reference for this entry.
            category (str): Echoes the category given.
    """
    digest = hashlib.sha256(f"{query_summary}|{category}".encode()).hexdigest()
    reference_id = digest[:8].upper()
    return {"logged": True, "reference_id": reference_id, "category": category}
```

## Step 7: Wire up the demo agent

Create `agents/lesson13a_skills/skills_demo/agent.py`

```python
"""Lesson 13a: Demo agent combining a Skill, a plain tool, and an AgentTool.
"""

from pathlib import Path

from google.adk.agents import Agent
from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor
from google.adk.skills import load_skill_from_dir
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.skill_toolset import SkillToolset

from common.model_config import get_model

from .credit_tools import get_credit_bureau_report, validate_pan_format
from .risk_specialist.agent import risk_specialist_agent
from .support_tools import record_customer_query

SKILLS_DIR = Path(__file__).resolve().parent / "skills"

loan_terms_glossary_skill = load_skill_from_dir(SKILLS_DIR / "loan-terms-glossary")
pan_credit_check_skill = load_skill_from_dir(SKILLS_DIR / "pan-credit-check")
emi_calculator_skill = load_skill_from_dir(SKILLS_DIR / "emi-calculator")

instruction = """You are a loan support assistant at an NBFC. You have
three kinds of capability available, not one:

1. Skills, for procedures: explaining a loan term in plain language,
   checking a PAN and credit history, or calculating an exact EMI.
   List and load these on demand when a request needs one, don't
   assume you already know the details.
2. A risk assessment specialist, for judgment: when a request needs a
   full risk score and band from an applicant's credit and loan
   details, delegate to the risk specialist tool rather than guessing.
3. Query logging, always available: after handling any customer
   request, call `record_customer_query` with a short summary and a
   category ("terms", "pan_credit", "emi", "risk", or "general"),
   every interaction gets logged, regardless of which of the above you
   used.
"""

# UnsafeLocalCodeExecutor runs whatever the model generates directly in
# this process, no sandbox. Fine here: you wrote calculate_emi.py
# yourself, and you're running this on your own machine while learning.
# Not something to point at untrusted input or run in production.
root_agent = Agent(
    name="skills_demo_agent",
    model=get_model("primary"),
    description="Handles loan support requests using skills, a risk specialist, and always-on query logging.",
    instruction=instruction,
    tools=[
        SkillToolset(
            skills=[loan_terms_glossary_skill, pan_credit_check_skill, emi_calculator_skill],
            additional_tools=[validate_pan_format, get_credit_bureau_report],
            code_executor=UnsafeLocalCodeExecutor(),
        ),
        record_customer_query,
        AgentTool(agent=risk_specialist_agent),
    ],
)
```

Three entries in `tools=[]`, three different kinds of thing. `SkillToolset` resolves to its four skill-management tools up front, and only adds `validate_pan_format`/`get_credit_bureau_report` once the model actually loads `pan-credit-check`, loading `loan-terms-glossary` instead adds nothing at all, confirmed directly, the tool list is identical before and after. `record_customer_query`, a plain function, and `AgentTool(agent=risk_specialist_agent)` are both present from the very first turn, no discovery step, no activation state, exactly the "always present" behavior Skills deliberately don't have. All three mechanisms resolve together into one list the model sees, with no special handling anywhere in this file, which is exactly the point the theory lesson made and this file now proves.

`code_executor` is what `run_skill_script` needs to exist at all, without it, `emi-calculator`'s script can't run.

> **NOTE:** `UnsafeLocalCodeExecutor` runs scripts using Python's `multiprocessing` with the `spawn` start method, which has a real, easy-to-hit requirement: whatever script ultimately drives this agent needs a proper `if __name__ == "__main__":` guard around its entry point. `main.py`, below, already has one. If you ever call this agent from a script or notebook that doesn't, `spawn` will try to re-import your file as if it were the child process's own entry point, and you'll get a `RuntimeError` about bootstrapping, not a bug in this lesson's code, a real Python `multiprocessing` constraint worth knowing about before it surprises you somewhere else.

## Step 8: Wire up main.py

Create `agents/lesson13a_skills/main.py`

```python
"""Lesson 13a: Run the skills demo agent.
"""

import asyncio
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # adds agents/ for common.*

from google.adk.sessions import InMemorySessionService

from common.runner_utils import run_agent_query
from skills_demo.agent import root_agent

APP_NAME = "lesson13a_skills"
USER_ID = "console_user"


async def main() -> None:
    """Runs the skills demo agent against console input."""
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())

    print("Loan support assistant (Skills, a plain tool, and an AgentTool).")
    print("Try asking what a loan term means, a PAN question, an EMI question, or a full risk assessment. Type 'quit' to exit.\n")

    loop = asyncio.get_event_loop()
    while True:
        try:
            user_input = await loop.run_in_executor(None, lambda: input("You: "))
        except EOFError:
            break

        if user_input.strip().lower() in ("quit", "exit"):
            break

        response = await run_agent_query(
            agent=root_agent,
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
            query=user_input,
            session_service=session_service,
        )
        print("Agent:", response, "\n")


if __name__ == "__main__":
    asyncio.run(main())
```

Nothing skill-specific in here at all, `run_agent_query` doesn't know or care that `root_agent`'s tools include a `SkillToolset`, an `AgentTool`, and a plain function all at once. That's the same story as `AgentTool` in 11d, once something's wrapped as a tool, whatever's driving the agent doesn't need to change.

## Step 9: Run it

```bash
uv run agents/lesson13a_skills/main.py
```

Try the simplest skill first:

```
You: What does moratorium mean on a loan?
```

The model should load `loan-terms-glossary` and answer straight from what it just read, no tool call anywhere in this turn, since none is available for this skill to unlock.

Then the instructions-only skill that does gate tools:

```
You: Is ABCDE1234F a valid PAN? If so, what's the credit history look like?
```

The model should list or load `pan-credit-check`, then call `validate_pan_format` and `get_credit_bureau_report`, tools that weren't in its list at the start of the conversation.

Then the scripted one:

```
You: What's the exact EMI on a loan of 500000 at 10.5% over 36 months?
```

This should load `emi-calculator` and run `calculate_emi.py` through `run_skill_script`, coming back with 16251.22, the exact figure the script computes, not an estimate.

Then the `AgentTool`:

```
You: Full risk check please: credit score 773, annual income 900000, loan amount 500000, tenure 36 months, no prior defaults.
```

This time there's no skill to list or load, `risk_specialist_agent` is already sitting in the tool list. You should get back a risk score around 82.7, band Low. Across all three of these, keep an eye on whether the model also calls `record_customer_query` afterward, that tool never needed listing or loading either, it was available from the very first turn of the conversation, same as the risk specialist.

## Try it in adk web too

```bash
adk web agents
```

Select `lesson13a_skills.skills_demo`. The trace panel here is worth lingering on more than usual: watch the tool calls for the PAN question, you should see `list_skills` or `load_skill` before `validate_pan_format` ever appears, direct, visible confirmation that the tool genuinely wasn't available until the skill was loaded, not just something the lesson claims happens. Compare that against the moratorium question's trace, `load_skill` still fires, but no new tool ever appears afterward, the visible difference between a skill that unlocks something and one that doesn't.

## If you're coming from LangChain or LangGraph

There's no single, standard equivalent here, this is closer to a plugin or extension system than anything LangChain ships as a core primitive. The closest comparison is a retrieval step that fetches relevant documentation before a task, except what's being fetched isn't reference material to read, it's instructions and tools the agent can actually act on, and the fetching is a tool call the model makes itself, not a pipeline step wired in ahead of time.

## In this lesson

You built three skills for real, spanning the full range this format actually covers. `loan-terms-glossary` was the simplest possible shape, instructions only, no `metadata`, no tools, confirmed directly that loading it changes nothing about the agent's available tools, only what the model has read. `pan-credit-check` packaged procedure and activated two plain Python functions on demand, tools that genuinely weren't part of the agent's tool list until the model chose to load that skill, verified directly rather than assumed. `emi-calculator` went further still, bundling an actual script, run through `UnsafeLocalCodeExecutor`, with the real `multiprocessing` constraint that comes with it. Then you put a `SkillToolset`, a plain always-on function tool, and an `AgentTool` wrapping a full risk specialist all in the same agent's `tools=[]` list at once, and watched the difference between them in practice, tools that had to be discovered and loaded, and tools that were just there from the first turn, all resolved together with nothing extra required anywhere in `main.py` or `adk web`.

## In the next lesson

Lesson 13b covers the one mechanism this pair of lessons hasn't demonstrated yet, `load_skill_resource`, loading real content out of a skill's own `references/` and `assets/` folders, rather than just activating a tool or running a script.
