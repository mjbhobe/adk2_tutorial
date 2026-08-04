# Lesson 11a: SequentialAgent in Practice

Quick recap: `SequentialAgent` runs a list of sub-agents one after another, in the exact order you give it. Every sub-agent shares the same session, so a later sub-agent can read what an earlier one wrote to state. No LLM sits behind the `SequentialAgent` itself, it's a plain orchestrator. You would use a `SequentialAgent` to mimic a multi-step workflow, where the steps must follow a strict sequence one-after-another, like a loan underwriting process. 

## The problem we're solving

You're building the loan underwriting pipeline for an NBFC (non-banking financial company), the exact one sketched in the last lesson. A loan application comes in as free text. Four things need to happen to it, in order:

1. **Intake** extracts structured fields from the text and validates the applicant's PAN (Permanent Account Number, India's tax ID and the standard identity check for financial applications).
2. **Credit check** fetches the applicant's credit bureau report using that PAN.
3. **Risk scoring** combines the bureau data with the applicant's income and the loan terms to produce a risk score.
4. **Decision** applies the underwriting rules and returns approve, reject, or refer to a human underwriter.

This is the pipeline we are going to be implementing:

![SequentialAgent Flow](images/sequential_agent_flow.png)

Each step depends on the one before it. Risk scoring is meaningless without a credit score to feed it. A decision is meaningless without a risk band to base it on. That dependency chain is exactly what `SequentialAgent` is for.

## How state actually flows through a SequentialAgent

You already know the mechanism in principle from Lesson 6a and Lesson 5: `output_key` writes an agent's result to session state, and `{key}` in a later agent's instruction reads it back. What's new here is seeing it drive an entire pipeline, plus two details that only show up once you actually build one.

Each of the four sub-agents in this lesson uses `output_schema` (a Pydantic model, from Lesson 5) together with `output_key`. That combination writes a validated, structured result to session state after every turn, no free text mixed in, and the next sub-agent's instruction reads it straight out of state.

> 📌 **NOTE:** When `output_schema` is set, ADK stores the validated result in session state as a plain Python dict, not as the Pydantic object and not as a JSON string. That matters for the next point.
>
> Instruction templating does a simple `str(value)` substitution. If `{credit_check_result}` resolves to a dict, what the model actually sees in its prompt is something like `{'pan_number': 'XYZAB3456C', 'credit_score': 690, ...}`. There's no nested access like `{credit_check_result.credit_score}`, you always get the whole dict as text, and the model reads the field it needs out of that text. This works fine in practice, Claude parses a printed dict without trouble, but it's worth knowing what's actually landing in the prompt. Your LLM of choice (the model) could behave differently, and it's worth nothing this point!

One more thing worth flagging before you write a line of code: as of ADK 2.5.0, the version this series targets, `SequentialAgent` prints a deprecation warning pointing to a newer `Workflow` class.

> **NOTE:** `SequentialAgent` is fully functional today, this lesson's code runs correctly on it. The warning exists because ADK is moving toward a more general graph-based `Workflow` primitive, which the series covers later, once you've got the classic workflow agents under your belt. The ADK source itself states that `Workflow` can't yet be used as a sub-agent of another agent, so the classic workflow agents remain the right tool for the kind of pipeline you're building today.

## Step 1: Set up the folder structure

Multi-agent lessons get their own nested layout, since there are now several agents living under one lesson. Create this structure under `agents/`:

```
agents/lesson11a_sequential_agent/
├── main.py
└── loan_pipeline/
    ├── __init__.py
    ├── agent.py
    └── sub_agents/
        ├── __init__.py
        ├── intake_agent/
        │   ├── __init__.py
        │   ├── agent.py
        │   └── tools.py
        ├── credit_check_agent/
        │   ├── __init__.py
        │   ├── agent.py
        │   └── tools.py
        ├── risk_scoring_agent/
        │   ├── __init__.py
        │   ├── agent.py
        │   └── tools.py
        └── decision_agent/
            ├── __init__.py
            ├── agent.py
            └── tools.py
```

`loan_pipeline/agent.py` is where the `SequentialAgent` itself gets assembled. Each of the four sub-agents gets its own folder underneath, with the same `agent.py` / `tools.py` split we've used since Lesson 3. Every `__init__.py` in this tree, at every level, contains exactly one line:

```python
from . import agent
```

That's the same convention you've used from Lesson 6a onward, it makes each folder's agent module reachable as an attribute of the package.

## Step 2: Build the intake agent

Start with the tool. Extracting fields from free text is squarely an LLM's job, but validating that a PAN matches the required format is not, that's a strict pattern match, and LLMs are unreliable at exact-format checks like this. Give it a tool instead.

```python
# agents/lesson11a_sequential_agent/loan_pipeline/sub_agents/intake_agent/tools.py
"""Lesson 11a: Tools for the intake agent.
"""

import re

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def validate_pan_format(pan_number: str) -> dict:
    """Validates that a string matches the Indian PAN (Permanent Account Number) format.

    A valid PAN is exactly 10 characters: 5 uppercase letters, 4 digits, then
    1 uppercase letter (e.g. ABCDE1234F). This checks the format only, it
    does not verify the PAN against any government registry.

    Args:
        pan_number: The PAN string extracted from the loan application.

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
```

Nothing new here beyond what Lesson 3 taught you about tools: a plain function, a Google-style docstring the model reads as the tool description, and a dict return with an `error` key for the failure case.

Now the agent itself:

```python
# agents/lesson11a_sequential_agent/loan_pipeline/sub_agents/intake_agent/agent.py
"""Lesson 11a: Intake agent for the loan underwriting pipeline.

Validates a raw loan application, extracts structured fields, and checks
the PAN format before handing off to the credit check agent.
"""

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import validate_pan_format


class IntakeResult(BaseModel):
    """Structured output of the intake agent."""

    applicant_name: str = Field(description="Full name of the loan applicant")
    pan_number: str = Field(description="Applicant's PAN (Permanent Account Number)")
    loan_amount: float = Field(description="Requested loan amount, in INR")
    tenure_months: int = Field(description="Requested loan tenure, in months")
    annual_income: float = Field(description="Applicant's declared annual income, in INR")
    purpose: str = Field(description="Stated purpose of the loan")
    is_complete: bool = Field(description="True only if every required field was present and the PAN was valid")
    missing_or_invalid_fields: list[str] = Field(
        default_factory=list,
        description="Names of any fields that were missing or failed validation",
    )


instruction = """You are the intake agent for a loan underwriting pipeline at an NBFC.

A loan application arrives as free-form text. Do the following:

1. Extract these fields from the text: applicant_name, pan_number, loan_amount,
   tenure_months, annual_income, purpose.
2. Call the `validate_pan_format` tool with the extracted pan_number. Never judge
   the PAN format yourself, always call the tool and use its result.
3. Set is_complete to True only if every field above was present in the
   application AND the tool reported the PAN as valid. Otherwise set it to
   False and list every missing or invalid field name in
   missing_or_invalid_fields.

Respond only with the structured fields. Do not add commentary outside them.
"""

root_agent = Agent(
    name="intake_agent",
    model=get_model("primary"),
    description="Extracts and validates loan application fields from free-form applicant input.",
    instruction=instruction,
    tools=[validate_pan_format],
    output_schema=IntakeResult,
    output_key="intake_result",
)
```

This is the pattern from Lesson 5, `output_schema` plus `output_key`, applied to the first step of a pipeline instead of a standalone agent. `IntakeResult` guarantees every downstream agent gets clean, typed fields to work with, no parsing free text later in the chain. `is_complete` and `missing_or_invalid_fields` exist specifically so the decision agent, four steps from now, has something concrete to check before it approves anything.

## Step 3: Build the credit check agent

The tool here simulates a call to a credit bureau. A real integration would hit an external API, this mocks one deterministically so the lesson is repeatable:

```python
# agents/lesson11a_sequential_agent/loan_pipeline/sub_agents/credit_check_agent/tools.py
"""Lesson 11a: Tools for the credit check agent.
"""

import hashlib


def get_credit_bureau_report(pan_number: str) -> dict:
    """Fetches a mock credit bureau report for an applicant.

    This simulates a call to a credit bureau (like CIBIL) using a
    deterministic hash of the PAN, so the same applicant (i.e. same PAN) always gets the
    same mock score. That makes the pipeline repeatable while you're
    learning. Swap this out for a real bureau API integration in production.

    Args:
        pan_number: The applicant's validated PAN number.

    Returns:
        A dict with:
            pan_number (str): The PAN the report was generated for.
            credit_score (int): A CIBIL-style score between 300 and 900.
            existing_loans_count (int): Number of currently active loans.
            has_defaults (bool): True if the mock history includes a default.
            error (str, optional): Present only if pan_number is empty.
    """
    if not pan_number:
        return {"error": "pan_number is required to fetch a credit bureau report."}

    digest = hashlib.sha256(pan_number.encode()).hexdigest()
    seed = int(digest[:8], 16)

    credit_score = 300 + (seed % 601)  # 300 to 900
    existing_loans_count = seed % 4  # 0 to 3
    has_defaults = (seed % 7) == 0  # roughly 1 in 7 applicants

    return {
        "pan_number": pan_number,
        "credit_score": credit_score,
        "existing_loans_count": existing_loans_count,
        "has_defaults": has_defaults,
    }
```

Hashing the PAN and deriving the mock values from it means the same applicant always gets the same report across runs, which makes debugging the pipeline far less confusing than random numbers would.

```python
# agents/lesson11a_sequential_agent/loan_pipeline/sub_agents/credit_check_agent/agent.py
"""Lesson 11a: Credit check agent for the loan underwriting pipeline.

Reads the intake agent's output from session state, fetches a mock credit
bureau report, and writes a structured credit check result.
"""

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import get_credit_bureau_report


class CreditCheckResult(BaseModel):
    """Structured output of the credit check agent."""

    pan_number: str = Field(description="PAN the bureau report was fetched for")
    credit_score: int = Field(description="CIBIL-style score, 300 to 900")
    existing_loans_count: int = Field(description="Number of currently active loans")
    has_defaults: bool = Field(description="True if the bureau history shows a prior default")


instruction = """You are the credit check agent for a loan underwriting pipeline at an NBFC.

The intake agent already ran. Its output is available in session state as:
{intake_result}

Read the pan_number out of it, then call the `get_credit_bureau_report` tool
with that PAN to fetch the applicant's credit bureau report. Return the
report exactly as the tool gives it back to you, in the structured fields.

Never fabricate a credit score yourself. Always call the tool.
"""

root_agent = Agent(
    name="credit_check_agent",
    model=get_model("primary"),
    description="Fetches an applicant's credit bureau report using the PAN captured during intake.",
    instruction=instruction,
    tools=[get_credit_bureau_report],
    output_schema=CreditCheckResult,
    output_key="credit_check_result",
)
```

`{intake_result}` in the instruction is the whole point of this exercise. By the time this agent runs, `SequentialAgent` has already completed the intake agent's full turn, tool call included, and written its output to state. This agent reads it straight out, no wiring required on your part.

## Step 4: Build the risk scoring agent

This is the step where you don't want the LLM doing arithmetic. Risk scores need to be consistent and auditable, so the actual formula lives in a tool, not in the model's head:

```python
# agents/lesson11a_sequential_agent/loan_pipeline/sub_agents/risk_scoring_agent/tools.py
"""Lesson 11a: Tools for the risk scoring agent.
"""


def calculate_risk_score(
    credit_score: int,
    annual_income: float,
    loan_amount: float,
    tenure_months: int,
    has_defaults: bool,
) -> dict:
    """Calculates a deterministic risk score for a loan application.

    Combines the bureau credit score with a rough affordability check, an
    approximate EMI (equated monthly installment) against monthly income.
    This is a simple dummy model, not a production underwriting formula, real
    risk models weigh many more factors and get validated by a risk team.

    Args:
        credit_score: CIBIL-style score between 300 and 900.
        annual_income: Applicant's declared annual income, in INR.
        loan_amount: Requested loan amount, in INR.
        tenure_months: Requested tenure, in months.
        has_defaults: Whether the bureau report shows a prior default.

    Returns:
        A dict with:
            risk_score (float): 0 to 100, higher means lower risk.
            risk_band (str): "Low", "Medium", or "High".
            emi_to_income_ratio (float): Approximate EMI as a fraction of
                monthly income.
            error (str, optional): Present only on invalid inputs.
    """
    if tenure_months <= 0 or annual_income <= 0:
        return {"error": "tenure_months and annual_income must both be positive."}

    credit_component = (credit_score / 900) * 60  # up to 60 points

    monthly_income = annual_income / 12
    approx_emi = loan_amount / tenure_months  # ignores interest, a deliberate simplification
    emi_to_income_ratio = round(approx_emi / monthly_income, 2)
    affordability_component = max(0.0, (1 - emi_to_income_ratio) * 40)  # up to 40 points

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

The formula is deliberately simple: up to 60 points from the credit score, up to 40 from how comfortably the applicant can afford the EMI, minus a 25-point penalty for a prior default. Real risk models are far more elaborate and get validated by an actual risk team before going anywhere near production, this version exists to give the pipeline something concrete and explainable to work with.

```python
# agents/lesson11a_sequential_agent/loan_pipeline/sub_agents/risk_scoring_agent/agent.py
"""Lesson 11a: Risk scoring agent for the loan underwriting pipeline.

Reads the intake and credit check results from session state and produces
a deterministic risk score and band.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import calculate_risk_score


class RiskScoringResult(BaseModel):
    """Structured output of the risk scoring agent."""

    risk_score: float = Field(description="Risk score from 0 to 100, higher means lower risk")
    risk_band: str = Field(description='One of "Low", "Medium", or "High"')
    emi_to_income_ratio: float = Field(description="Approximate EMI as a fraction of monthly income")


instruction = """You are the risk scoring agent for a loan underwriting pipeline at an NBFC.

Session state has two prior results.

Intake result:
{intake_result}

Credit check result:
{credit_check_result}

Pull annual_income, loan_amount, and tenure_months from the intake result, and
credit_score plus has_defaults from the credit check result. Call the
`calculate_risk_score` tool with those five values. Return the tool's result
exactly, in the structured fields.

Always call the tool. Never estimate the score yourself.
"""

root_agent = Agent(
    name="risk_scoring_agent",
    model=get_model("primary"),
    description="Calculates a deterministic risk score and band from intake and credit bureau data.",
    instruction=instruction,
    tools=[calculate_risk_score],
    output_schema=RiskScoringResult,
    output_key="risk_scoring_result",
)
```

Notice this agent reads from two prior state keys, `{intake_result}` and `{credit_check_result}`, not just the one immediately before it. `SequentialAgent` doesn't restrict you to only reading the previous step's output, every sub-agent shares the same session, so anything written earlier in the pipeline stays readable for the rest of it.

## Step 5: Build the decision agent

The final step. Its tool is a simple rate card lookup:

```python
# agents/lesson11a_sequential_agent/loan_pipeline/sub_agents/decision_agent/tools.py
"""Lesson 11a: Tools for the decision agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

_RATE_CARD = {
    "Low": 10.5,
    "Medium": 13.5,
}


def lookup_interest_rate(risk_band: str) -> dict:
    """Looks up the interest rate offered for a given risk band.

    A stand-in for a real rate card lookup. In production this would read
    from a pricing service that moves with market conditions, not a fixed
    dict.

    Args:
        risk_band: One of "Low", "Medium", or "High".

    Returns:
        A dict with:
            risk_band (str): The band that was looked up.
            eligible (bool): False for "High" risk, no rate is offered.
            interest_rate (float, optional): Annual interest rate as a
                percentage, present only when eligible is True.
            error (str, optional): Present only for an unrecognized band.
    """
    if risk_band not in ("Low", "Medium", "High"):
        return {"error": f"Unknown risk_band '{risk_band}'."}

    if risk_band == "High":
        return {"risk_band": risk_band, "eligible": False}

    return {
        "risk_band": risk_band,
        "eligible": True,
        "interest_rate": _RATE_CARD[risk_band],
    }
```

```python
# agents/lesson11a_sequential_agent/loan_pipeline/sub_agents/decision_agent/agent.py
"""Lesson 11a: Decision agent for the loan underwriting pipeline.

Reads all three prior results from session state and produces the final
loan decision.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from google.adk.agents import Agent

from common.model_config import get_model

from .tools import lookup_interest_rate


class DecisionResult(BaseModel):
    """Structured output of the decision agent."""

    decision: Literal["approved", "rejected", "refer_to_underwriter"] = Field(
        description="Final outcome of the loan application"
    )
    interest_rate: Optional[float] = Field(
        default=None, description="Annual interest rate offered, present only when approved"
    )
    reasons: list[str] = Field(description="Short, specific reasons behind the decision")


instruction = """You are the decision agent, the final step in a loan
underwriting pipeline at an NBFC.

Session state has three prior results.

Intake result:
{intake_result}

Credit check result:
{credit_check_result}

Risk scoring result:
{risk_scoring_result}

Apply these rules in order:

1. If the intake result's is_complete is False, decision is
   "refer_to_underwriter". Reason: incomplete application data.
2. Otherwise, call the `lookup_interest_rate` tool with the risk_band from
   the risk scoring result.
3. If the tool reports eligible as False, decision is "rejected".
4. If the tool reports eligible as True, decision is "approved", and
   interest_rate is the rate the tool returned.

Always call the tool before approving, never guess the rate yourself. In
reasons, reference the actual risk_band, credit_score, and
emi_to_income_ratio values you were given, not generic statements.
"""

root_agent = Agent(
    name="decision_agent",
    model=get_model("primary"),
    description="Applies the underwriting rules and produces the final loan decision.",
    instruction=instruction,
    tools=[lookup_interest_rate],
    output_schema=DecisionResult,
    output_key="decision_result",
)
```

By this point the instruction has three state keys to read from, and the rules are written as an explicit numbered sequence rather than left for the model to infer. The more a step resembles a policy you could hand to a new employee on day one, the more it helps to write it that literally in the instruction.

## Step 6: Assemble the SequentialAgent

This is the step that turns four separate agents into one pipeline:

```python
# agents/lesson11a_sequential_agent/loan_pipeline/agent.py
"""Lesson 11a: SequentialAgent that chains the loan underwriting pipeline.

Runs intake, credit check, risk scoring, and decision agents in a fixed
order, using session state to pass each step's output to the next.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import SequentialAgent

from .sub_agents.intake_agent import agent as intake_agent_module
from .sub_agents.credit_check_agent import agent as credit_check_agent_module
from .sub_agents.risk_scoring_agent import agent as risk_scoring_agent_module
from .sub_agents.decision_agent import agent as decision_agent_module

root_agent = SequentialAgent(
    name="loan_underwriting_pipeline",
    description="Runs a loan application through intake, credit check, risk scoring, and decision, in order.",
    sub_agents=[
        intake_agent_module.root_agent,
        credit_check_agent_module.root_agent,
        risk_scoring_agent_module.root_agent,
        decision_agent_module.root_agent,
    ],
)
```

`SequentialAgent` takes a `name`, a `description`, and the `sub_agents` list, that's the entire declaration. The order of that list is the order the pipeline runs in, this is the one place in this file where list order carries real meaning. Each sub-agent's own `agent.py` file did the actual work of defining what that step does, this file's only job is to put them in a line.

## Step 7: Wire up main.py

Same shape as every `main.py` you've written since Lesson 6a: `load_dotenv`, a `sys.path` insert so `common.*` resolves, `InMemorySessionService`, and an async console loop that calls `run_agent_query` from `agents/common/runner_utils.py`.

```python
# agents/lesson11a_sequential_agent/main.py
"""Lesson 11a: Run the loan underwriting SequentialAgent pipeline.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
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
from loan_pipeline.agent import root_agent

APP_NAME = "lesson11a_sequential_agent"


async def main() -> None:
    """Runs the loan underwriting pipeline against console input."""
    session_service = InMemorySessionService()
    user_id = "console_user"
    session_id = str(uuid.uuid4())

    print("Loan underwriting pipeline (SequentialAgent).")
    print("Paste a loan application as free text, or type 'quit' to exit.\n")

    loop = asyncio.get_event_loop()
    while True:
        try:
            user_input = await loop.run_in_executor(None, lambda: input("Application: "))
        except EOFError:
            break

        if user_input.strip().lower() in ("quit", "exit"):
            break

        response = await run_agent_query(
            agent=root_agent,
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            query=user_input,
            session_service=session_service,
        )
        print(f"\nPipeline: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
```

`run_agent_query` takes `root_agent`, the `SequentialAgent`, exactly the same way it's always taken a single `Agent`. That's the practical payoff of workflow agents being `BaseAgent` subclasses too: the `Runner` and the rest of your infrastructure don't need to know or care that they're driving four agents instead of one.

## Step 8: Run it

```bash
uv run agents/lesson11a_sequential_agent/main.py
```

Paste in a loan application as plain text, something like:

```
Application: Ananya Rao is applying for a home renovation loan of INR 400000
over 48 months. Her PAN is XYZAB3456C and her annual income is INR 1500000.
```

Watch the pipeline run through all four steps, intake, credit check, risk scoring, decision, and print the final structured result. With this particular applicant, you should see something close to: PAN validated, a credit score around 690 with no prior defaults, a risk score in the low-risk band, and an approved decision with an interest rate of 10.5%.

Try a second application with a much smaller income relative to the loan amount, or a fabricated PAN like `NOTAPAN123`, and watch the decision change. An invalid PAN should push `is_complete` to `False` at the intake step and come out the other end as `refer_to_underwriter`, without the pipeline ever reaching the credit check or risk scoring agents' actual banking logic in a meaningful way, since the whole point of a bad `is_complete` is that the decision agent short-circuits on it.

## If you're coming from LangChain or LangGraph

In LangGraph, this same pipeline would be a `StateGraph` with a shared `TypedDict` state, four nodes (one function per step), and edges added between them in a straight line, `intake → credit_check → risk_scoring → decision`, before compiling and invoking the graph. Each node reads from and writes to the same state dict, conceptually close to what `{intake_result}` and `output_key` are doing here.

The difference is in what you write by hand. LangGraph makes you define the state schema, the node functions, and the edges explicitly, you're describing a graph. ADK's `SequentialAgent` skips the graph-drawing step for this specific shape: you give it a `name` and an ordered `sub_agents` list, and it enforces both the order and the state propagation for you.

## In this lesson

You built a working four-agent `SequentialAgent` pipeline for loan underwriting: intake, credit check, risk scoring, and decision, each its own small agent with its own tool and structured output. You saw `output_schema` and `output_key` chain results across steps through session state, and picked up two details that only show up once you build one of these for real: state gets stored as a plain dict, and instruction templating stringifies it rather than giving you nested field access. You also saw that `SequentialAgent` still works cleanly today, deprecation warning aside, and why that warning doesn't change anything about this lesson's code.

## In the next lesson

The next lesson moves from strict ordering to concurrency. You'll build the KYC (Know Your Customer) onboarding example from earlier with `ParallelAgent`, running the credit bureau, fraud watchlist, and document verification checks at the same time instead of one after another, and see firsthand what changes when sub-agents can't rely on turn order to avoid stepping on each other's state.
