"""Lesson 7a: Callbacks in Practice.

All six callback functions for the wealth management advisory agent,
kept in their own file so agent.py stays focused on what the agent
IS (its model, instruction, and tools) rather than what it DOES at
each interception point. Import these into agent.py; don't call them
from anywhere else directly, since ADK is the one doing the calling.

CRITICAL: ADK calls every callback using keyword arguments that must
match your parameter names exactly. The enforced names are:
  before_agent_callback / after_agent_callback : callback_context
  before_model_callback                        : callback_context, llm_request
  after_model_callback                         : callback_context, llm_response
  before_tool_callback                         : tool, args, tool_context
  after_tool_callback                          : tool, args, tool_context, tool_response

Using any other name raises a TypeError at runtime, not at import time.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types

# ── Before Agent ──────────────────────────────────────────────────────────────
# Mandatory parameter name: callback_context
# Fires: once per turn, before anything else.
# Returns Content to short-circuit the turn; returns None to proceed.


async def check_customer_tier(callback_context: CallbackContext):
    """Blocks access for unrecognised account tiers and tracks turn count.

    This is the right place for access control: no model tokens are
    spent if the request is going to be blocked anyway, and session
    bookkeeping here applies regardless of what the customer said.
    """
    valid_tiers = {"Standard", "Gold", "Platinum"}
    tier = callback_context.state.get("account_tier", "")

    if tier not in valid_tiers:
        return types.Content(
            role="model",
            parts=[
                types.Part(
                    text=(
                        "Sorry, I'm unable to verify your account tier. "
                        "Please contact your branch for assistance."
                    )
                )
            ],
        )

    callback_context.state["turn_count"] = (
        callback_context.state.get("turn_count", 0) + 1
    )
    return None


# ── Before Model ──────────────────────────────────────────────────────────────
# Mandatory parameter names: callback_context, llm_request
# Fires: once per model call. In a turn with tools, fires MULTIPLE TIMES:
#   once before the model requests tools, and again before it generates
#   its final answer with tool results in context.
# Returns LlmResponse to skip the model call; returns None to proceed.


async def inject_market_context(callback_context: CallbackContext, llm_request):
    """Injects current market status into the system prompt dynamically.

    Only injects on the first model call per turn (before any tools have
    run). On the second call (after tool results are in context), skips
    the injection to avoid duplicating the market note.

    Note: the system instruction lives at llm_request.config.system_instruction,
    not directly on llm_request. We use the built-in append_instructions()
    method to add context cleanly rather than mutating parts directly.
    """
    has_tool_results = any(
        hasattr(msg, "parts")
        and any(
            hasattr(p, "function_response") and p.function_response
            for p in (msg.parts or [])
        )
        for msg in (llm_request.contents or [])
    )

    if not has_tool_results:
        market_note = (
            "Current market snapshot: BSE Sensex: 74,823 | "
            "Nifty50: 22,651 | S&P 500: 5,213. Markets are open."
        )
        llm_request.append_instructions([market_note])

    return None


# ── After Model ───────────────────────────────────────────────────────────────
# Mandatory parameter names: callback_context, llm_response
# Fires: once per model call (same multi-fire behaviour as before_model).
# Returns LlmResponse to replace the model's response; returns None to keep it.


async def scan_for_unsupported_advice(callback_context: CallbackContext, llm_response):
    """Scans model output for specific investment advice language.

    This agent can discuss portfolios and market data but cannot give
    specific buy or sell recommendations. If the model output contains
    such language, replaces the response with a compliant one.
    """
    prohibited_phrases = [
        "i recommend buying",
        "you should sell",
        "i suggest purchasing",
    ]

    if not llm_response.content or not llm_response.content.parts:
        return None

    response_text = " ".join(
        p.text.lower() for p in llm_response.content.parts if p.text
    )

    if any(phrase in response_text for phrase in prohibited_phrases):
        from google.adk.models.llm_response import LlmResponse

        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=(
                            "I can share factual information about your portfolio "
                            "and current market conditions, but I'm not able to make "
                            "specific buy or sell recommendations. Please speak with "
                            "your relationship manager for personalised advice."
                        )
                    )
                ],
            )
        )

    return None


# ── Before Tool ───────────────────────────────────────────────────────────────
# Mandatory parameter names: tool, args, tool_context
# (NOT "tool_args" — the parameter is exactly "args")
# Fires: once per tool call. Can fire multiple times in one turn.
# Returns a dict to skip the tool; returns None to let it run.


async def log_tool_invocation(tool, args: dict, tool_context: ToolContext):
    """Logs every tool call to the session audit trail.

    Records tool name and arguments before the tool runs, so the log
    is accurate even if the tool later fails or its result is replaced
    by after_tool_callback.
    """
    audit_log = tool_context.state.get("audit_log", [])
    audit_log.append({"tool": tool.name, "args": args})
    tool_context.state["audit_log"] = audit_log
    return None


# ── After Tool ────────────────────────────────────────────────────────────────
# Mandatory parameter names: tool, args, tool_context, tool_response
# Fires: once per tool call.
# Returns a dict to replace the tool's result; returns None to keep it.


async def validate_tool_result(
    tool, args: dict, tool_context: ToolContext, tool_response: dict
):
    """Validates tool results before the model sees them.

    Catches obviously invalid data and replaces it with a structured
    error the model can handle gracefully.
    """
    if tool.name == "get_portfolio_summary":
        total = tool_response.get("total_value", 0)
        if isinstance(total, (int, float)) and total <= 0:
            return {
                "found": False,
                "error": (
                    "Portfolio data returned an invalid value. "
                    "Please try again or contact support."
                ),
            }
    return None


# ── After Agent ───────────────────────────────────────────────────────────────
# Mandatory parameter name: callback_context
# Fires: once per turn, after the agent's final response is ready.
# Returns Content to replace the final response; returns None to keep it.


async def save_to_memory(callback_context: CallbackContext):
    """Saves this turn to long-term memory for future session recall.

    Requires a memory_service to be wired into the Runner in main.py.
    Without one, this raises a ValueError at runtime.
    """
    await callback_context.add_session_to_memory()
    return None
