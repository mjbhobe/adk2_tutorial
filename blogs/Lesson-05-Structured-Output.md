# Lesson 5: Structured Output

Lesson 4 gave an agent access to live data and current web information. Everything it produced, though, was still free-form text: a paragraph explaining a price, a summary of some news. That's fine for a chat interface, but it breaks down the moment an agent's output needs to feed into something else, a database, an approval workflow, a compliance report, that expects a predictable shape every single time. This lesson fixes that with structured output.

## The problem we're solving

A retail bank's underwriting desk has loan officers reviewing applicant files and writing up a risk assessment for each one: a risk tier, a recommendation, a note on the key concerns. Today _that write-up is free text, and free text is a real operational problem here_. One officer writes "high risk, wouldn't approve," another writes "Risk: High. Recommend decline. Reasons: thin credit history, high DTI." Nothing downstream, the approval queue, the audit trail, the regulator-facing report, can reliably parse either one, because there's no guaranteed structure. Someone ends up manually re-keying every assessment into a spreadsheet before it's usable anywhere else.

We're going to build an agent that produces a credit risk assessment as its output, but instead of a paragraph, it returns a fixed, validated JSON shape every time: a risk tier that's always one of three exact values, a boolean recommendation, a maximum recommended loan amount, a list of specific risk factors, and a short rationale. Every field, every time, in the same shape, ready to be written straight into a database row or an API call without anyone touching it by hand.

## Why structured output needs special handling

Left alone, an LLM's output is just text, and text is inherently unpredictable in its exact shape. You can ask a model nicely to _"please respond in JSON with these fields,"_. Modern models are decent at following that instruction, but "decent" isn't good enough for a downstream system that will throw an error, or silently accept garbage, the moment a field is missing, misspelled, or comes back as a string instead of a number. Prompting alone gives you a JSON-shaped suggestion, **not a guarantee**.

ADK's `output_schema` closes that gap by working at a different level than the prompt. You define the exact shape you want as a Pydantic model, a Python class describing each field's name, type, and (optionally) a description. When you attach that schema to an agent, ADK passes it to the model as a formal constraint on the response, not just an instruction in the prompt text, and validates the model's final answer against it. If the response doesn't match the schema, that's a failure ADK can catch, rather than something a downstream system finds out about the hard way, three steps later, after a $0 has silently made it into a loan amount field.

One thing worth knowing before we write the code: in earlier ADK guidance, `output_schema` and `tools` were described as mutually exclusive on the same agent, since forcing a fixed output shape and giving the model room to call functions used to be in tension with each other. That's no longer true in the version we're using. ADK now lets an agent use tools freely during its reasoning, and only enforces the schema on the final answer it hands back to you. That's exactly the shape our underwriting agent needs: call a tool to get real numbers, then produce a guaranteed-shape verdict.

## Step 1: Write the debt-to-income calculator

This lesson's tool is scoped narrowly to this agent, so it lives in the lesson's own `tools.py` rather than the shared `common` package.

Create the folder:

```bash
mkdir -p agents/lesson05_credit_risk
```

Create `agents/lesson05_credit_risk/tools.py`:

```python
"""Debt-to-income calculation for the credit risk assessment agent."""


def calculate_debt_to_income_ratio(
    monthly_income: float,
    total_monthly_debt_payments: float,
) -> dict:
    """Calculates a debt-to-income (DTI) ratio, a standard credit risk metric.

    DTI is one of the most widely used inputs in retail credit
    underwriting: it measures what share of a borrower's income is
    already committed to debt payments before any new loan.

    Args:
        monthly_income: The applicant's gross monthly income.
        total_monthly_debt_payments: The sum of all the applicant's
            existing monthly debt obligations, including any loan
            they're currently applying for on top of that.

    Returns:
        A dict with the DTI ratio as a percentage, or an error if the
        income given was zero or negative.
    """
    if monthly_income <= 0:
        return {"error": "monthly_income must be a positive number."}

    dti_percent = (total_monthly_debt_payments / monthly_income) * 100

    return {
        "debt_to_income_ratio_percent": round(dti_percent, 2),
        "monthly_income": monthly_income,
        "total_monthly_debt_payments": total_monthly_debt_payments,
    }
```

Nothing new here structurally, this is the same pattern from Lesson 3: a typed function with a clear docstring, returning a dict.

## Step 2: Define the output schema and build the agent

Create `agents/lesson05_credit_risk/agent.py`:

```python
"""Lesson 5: Structured Output.

A credit risk assessment agent for a retail bank's underwriting desk.
It calls a tool to compute a real debt-to-income ratio, then returns
its verdict as a validated, fixed-shape JSON object rather than free
text, so the result can be written straight into an approval system
without manual re-entry.
"""

from typing import Literal

from google.adk.agents import Agent
from pydantic import BaseModel, Field

from common.model_config import get_model
from .tools import calculate_debt_to_income_ratio


class CreditRiskAssessment(BaseModel):
    """The fixed shape every underwriting verdict from this agent must match."""

    risk_tier: Literal["Low", "Medium", "High"] = Field(
        description="The applicant's overall credit risk tier."
    )
    is_recommended_for_approval: bool = Field(
        description="Whether the agent recommends approving this application."
    )
    max_recommended_loan_amount: float = Field(
        description=(
            "The maximum loan amount the agent recommends approving for "
            "this applicant, given their income and existing obligations."
        )
    )
    key_risk_factors: list[str] = Field(
        description=(
            "Specific factors driving the risk tier, e.g. 'high "
            "debt-to-income ratio' or 'limited credit history'."
        )
    )
    rationale: str = Field(
        description="A short, plain-language explanation of the assessment."
    )


AGENT_INSTRUCTION = (
    "You are a credit risk assessment assistant for a retail bank's "
    "underwriting desk. Given an applicant's financial details, use "
    "the calculate_debt_to_income_ratio tool to compute their DTI "
    "before forming a judgment; never estimate this ratio yourself. "
    "As a general guideline, a DTI under 35% is typically Low risk, "
    "35-45% is typically Medium risk, and above 45% is typically High "
    "risk, though you should weigh other details the applicant "
    "mentions, such as employment stability or credit history, "
    "alongside the DTI rather than relying on it alone. Always "
    "provide specific, concrete risk factors, not vague statements."
)

root_agent = Agent(
    name="credit_risk_agent",
    model=get_model("primary"),
    instruction=AGENT_INSTRUCTION,
    description=(
        "Assesses retail loan applicant credit risk and returns a "
        "structured, validated verdict for the underwriting desk."
    ),
    tools=[calculate_debt_to_income_ratio],
    output_schema=CreditRiskAssessment,
)
```

Create `agents/lesson05_credit_risk/__init__.py`:

```python
from . import agent
```

The `CreditRiskAssessment` class is the new concept in this lesson, so it's worth going through field by field. Each field's Python type becomes a hard constraint on the response: `risk_tier` uses `Literal["Low", "Medium", "High"]` rather than a plain `str`, which tells ADK the value must be exactly one of those three strings, nothing else, no "Moderate" or "high risk" sneaking in. `is_recommended_for_approval` being a `bool` means you get a real `true`/`false` your code can branch on directly, not a sentence you'd have to parse. `key_risk_factors` being `list[str]` guarantees you get an actual array back, even if the model only identifies one risk factor or several.

The `Field(description=...)` on each attribute isn't decoration, it's read by the model as part of the schema, and it's the main lever you have over how a field gets filled in beyond the type itself. Compare this to Lesson 3's docstrings: there, the whole docstring became one block of context for a tool call. Here, each field's description is attached to that specific field in the schema the model receives, so this is actually more targeted guidance than what a plain docstring gives you for a function tool.

Notice that `tools=[calculate_debt_to_income_ratio]` and `output_schema=CreditRiskAssessment` sit on the agent together. Internally, ADK lets the model call the `calculate_debt_to_income_ratio` tool as many times as it needs while it works through the applicant's numbers, and only locks the response down to the `CreditRiskAssessment` shape once it's ready to give its final answer. You don't have to do anything to coordinate that sequencing yourself, it's handled automatically based on the two parameters you set.

## Step 3: Run it

```bash
# ensure your correct environment is activated
source .venv/bin/activate
# run it in adk web 
uv run adk web agents
```

Select `lesson05_credit_risk` from the dropdown and describe an applicant:

```
Applicant has a monthly income of 120,000, existing monthly debt payments of 55,000 including the new loan, 3 years at their current employer, and no missed payments on record.
```

You should see the agent call `calculate_debt_to_income_ratio` first, and then, instead of a written paragraph, the final response should render as a structured object with all five fields filled in: a risk tier, a true/false recommendation, a maximum recommended amount, a list of specific risk factors, and a short rationale. In `adk web` specifically, structured output like this typically renders as a clean, labeled JSON block rather than prose, which makes it obvious at a glance that you're looking at something different from Lesson 4's free-text answers.

Here is what I see:

<div align="center">
    <image src="images/credit_check1.png" alt="Credit Check - Claude"/>
</div>

Try a second applicant with a clearly lower DTI and a longer employment history, and compare the two verdicts. You should see the risk tier and recommendation shift accordingly, while the shape of the response, the five fields, their types, stays identical both times. That consistency is the entire point of this lesson.

```
Applicant has a monthly income of 150,000, existing monthly debt payments of 30,000 including the new loan, 8 years at their current employer, and no missed payments on record.
```

And here is what I see for this prompt

<div align="center">
    <image src="images/credit_check2.png" alt="Credit Check - Claude"/>
</div>

And for this prompt (High risk category):

```
Applicant has a monthly income of 60,000, existing monthly debt payments of 42,000 including the new loan, only 4 months at their current employer, and two missed payments on other loans in the past year.
```

And this is what I see.

<div align="center"> 
    <image src="images/credit_check3.png" alt="Credit Check 3- Claude"/>
</div>


## If you're coming from LangChain or LangGraph

This maps directly to LangChain's `with_structured_output()`, which also takes a Pydantic model and constrains a model's response to match it. The underlying idea, define your schema once as a Pydantic class and let the framework handle getting the model to conform to it, is identical across both frameworks. Where ADK's version stands out a bit is exactly the caveat from earlier in this lesson: combining a schema with active tool use in the same agent used to be more awkward to coordinate by hand, and here it's a native, built-in combination you get by setting two parameters.

## In this lesson

We moved an agent's output from free-form text to a validated, fixed-shape result. The underwriting agent still calls a real tool to ground its numbers, exactly as in Lesson 3, but now its final answer is a `CreditRiskAssessment` object with a guaranteed set of fields and types, not a paragraph someone has to interpret or re-key by hand. That's what makes an agent's output usable by the rest of a real system, rather than only usable by a person reading a chat window.

## In the next lesson

Lesson 6 picks up something every example so far has been missing: memory within a conversation. Every agent we've built forgets everything the moment a new message arrives, unless the conversation happens to still be in the same chat window. We'll build a multi-turn KYC (Know Your Customer) onboarding agent that actually remembers what it's already collected from a customer as the conversation continues, using ADK's session and state management.
