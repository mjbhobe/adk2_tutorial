"""Shared model-loading helper for every agent in this project.

Reads config/models.yaml once and returns a ready-to-use model value
(either a plain string for Gemini or an AnthropicLlm instance for
Claude) for a given policy tier: "primary", "escalation", or "fallback".

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from pathlib import Path
from typing import Literal

import yaml
from google.adk.models.anthropic_llm import AnthropicLlm

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
print(f"Project root: {_PROJECT_ROOT}")
_MODELS_CONFIG_PATH = _PROJECT_ROOT / "config" / "models.yaml"
print(f"Models config path: {_MODELS_CONFIG_PATH}")

ModelTier = Literal["primary", "escalation", "fallback"]


def get_model(tier: ModelTier = "primary"):
    """Builds the model object for the requested tier in config/models.yaml.

    Args:
        tier: Which entry in config/models.yaml to use. "primary" is
            Claude Haiku by default, "escalation" is Claude Sonnet,
            and "fallback" is Gemini Flash.

    Returns:
        Either a plain model name string (for Gemini, which ADK
        resolves natively) or an AnthropicLlm instance (for Claude,
        which needs to be constructed explicitly to use a direct
        Anthropic API key instead of Vertex AI).
    """
    with open(_MODELS_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    entry = config["models"][tier]
    provider = entry["provider"]
    model_id = entry["id"]

    print(f"Retrieving model for tier '{tier}': {provider} - {model_id}")

    if provider == "anthropic":
        print(f"get_model() will return -> AnthropicLlm({model_id})")
        return AnthropicLlm(model=model_id)
    if provider == "google":
        print(f"get_model() will return -> {model_id} [google]")
        return model_id

    raise ValueError(f"Unknown model provider '{provider}' for tier '{tier}'")
