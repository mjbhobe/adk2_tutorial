"""Lesson 2: Your First Agent.

A minimal agent that answers general banking terminology questions for
a retail bank's customer support desk.

Everything here is hardcoded on purpose. Starting in Lesson 3, model
choice and instructions move into config/models.yaml and per-agent
config, so agents stop needing code changes to swap models.

We are showing how to tweak it's hyperparameters to control behavior.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents import Agent
from google.adk.models.anthropic_llm import AnthropicLlm
from google.genai import types

# Flip this to True to run the exact same agent on Gemini Flash instead
# of Claude Haiku. Both API keys are already available from the
# project's root .env file!
USE_GEMINI_FLASH = True

AGENT_INSTRUCTION = (
    "You are a friendly, knowledgeable assistant for a retail bank's "
    "customer support desk. Answer questions about common banking "
    "terms and concepts, things like APR, EMI, KYC, and overdraft, "
    "in plain language a first-time customer would understand. Keep "
    "answers under 100 words. If a question requires looking at a "
    "specific customer's account or transaction data, say so clearly "
    "rather than guessing, since you don't have access to that data "
    "yet in this lesson."
)

if USE_GEMINI_FLASH:
    model = "gemini-3.5-flash-lite"
else:
    model = AnthropicLlm(model="claude-haiku-4-5-20251001")

print(f"NOTE: we are using the {model} model")

# Standardized generation hyperparameters for ADK 2.5.0
generation_config = types.GenerateContentConfig(
    temperature=0.1,
    max_output_tokens=256,
    top_p=0.9,
    top_k=40,
)

# NOTE: the "main" agent must be assigned to a variable called root_agent (case sensitive)
# This application uses just one agent, so it may not make much sense now. Will be clear when
# we develop multi-agent systems.

root_agent = Agent(
    name="bfsi_support_desk_agent_tuned",
    model=model,
    instruction=AGENT_INSTRUCTION,
    description="Answers general retail banking terminology questions.",
    generate_content_config=generation_config,
)
