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

instruction = """You are a loan support assistant at an NBFC. Every
customer message needs two things from you, in this order:

1. A real, substantive answer to what they actually asked. For loan
   terminology, checking a PAN and credit history, or calculating an
   exact EMI, load the relevant skill first and use what it tells you,
   don't assume you already know the details. For a full risk
   assessment, delegate to the risk assessment specialist tool instead
   of guessing.
2. Only after you've actually answered, call `record_customer_query`
   with a short summary and a category ("terms", "pan_credit", "emi",
   "risk", or "general"). Logging happens in addition to answering the
   customer, never instead of it.
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
            skills=[
                loan_terms_glossary_skill,
                pan_credit_check_skill,
                emi_calculator_skill,
            ],
            additional_tools=[validate_pan_format, get_credit_bureau_report],
            code_executor=UnsafeLocalCodeExecutor(),
        ),
        record_customer_query,
        AgentTool(agent=risk_specialist_agent),
    ],
)
