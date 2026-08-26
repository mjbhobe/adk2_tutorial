"""
Lesson 16a: the draft_notification agent

Defines the structured output schema and the single_turn Agent that
drafts the customer-facing message for a loan decision.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from pydantic import BaseModel

from google.adk.agents import Agent

from common.model_config import get_model


def _trigger_structured_output() -> str:
    """Placeholder tool, never meant to be called.

    See the explanation below the code listing for why this exists.

    Returns:
        A string that should never be seen.
    """
    return "not used"


class NotificationMessage(BaseModel):
    """The structured shape draft_notification_agent must return.

    Attributes:
        subject: A short subject line for the notification.
        body: The full message body, plain language.
    """

    subject: str
    body: str


INSTRUCTION = """You are a loan operations assistant.
You will receive a JSON object describing a loan decision, with keys
`net_disbursement` and `status`. `status` is either `AUTO_DISBURSED` or
`PENDING_MANUAL_REVIEW`.

Write a short customer-facing notification about this decision. Keep
the tone plain and reassuring, no jargon. If the status is
`AUTO_DISBURSED`, confirm the amount and that funds are on the way.
If it is `PENDING_MANUAL_REVIEW`, explain that the loan needs a quick
compliance check before funds move, without alarming the customer.
"""

draft_notification_agent = Agent(
    name="draft_notification_agent",
    model=get_model("primary"),
    description="Drafts a structured customer notification for a loan decision.",
    instruction=INSTRUCTION,
    tools=[_trigger_structured_output],
    output_schema=NotificationMessage,
)
# No mode= set here on purpose. A standalone Agent used directly as a
# workflow node, with no parent agent, defaults to mode='single_turn'.
