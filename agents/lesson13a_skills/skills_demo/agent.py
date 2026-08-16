"""Lesson 13a: Demo agent combining a Skill, a plain tool, and an AgentTool.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
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
