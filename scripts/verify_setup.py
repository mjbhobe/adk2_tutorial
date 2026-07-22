"""Verifies the ADK environment is correctly configured.

Checks three things, in order: the ADK CLI is installed, required
environment variables are present, and the Anthropic API key can
successfully reach Claude Haiku with a minimal request.

This script intentionally avoids importing google.adk.agents, since
building an actual Agent is the subject of Lesson 2.
"""

import os
import subprocess
import sys

from dotenv import load_dotenv


def check_adk_cli_installed() -> bool:
    """Confirms the `adk` command is available on PATH.

    Returns:
        bool: True if `adk --version` runs successfully.
    """
    try:
        result = subprocess.run(
            ["adk", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"[OK] ADK CLI installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        print(f"[FAIL] ADK CLI not found or errored: {error}")
        return False


def check_required_env_vars() -> bool:
    """Confirms the API keys needed for this series are present.

    Returns:
        bool: True if both keys are set and non-empty.
    """
    required = ["ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    missing = [name for name in required if not os.environ.get(name)]

    if missing:
        print(f"[FAIL] Missing environment variables: {', '.join(missing)}")
        return False

    print("[OK] Required environment variables are set")
    return True


def check_claude_connectivity() -> bool:
    """Sends one minimal request to Claude Haiku via the Anthropic SDK.

    This costs a fraction of a cent and confirms your Anthropic key
    is valid before you build anything on top of it. We call the
    Anthropic SDK directly here, matching ADK's native Claude provider
    (google.adk.models.anthropic_llm), so this test reflects exactly
    what ADK will do at runtime.

    Returns:
        bool: True if Claude responds successfully.
    """
    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        reply = response.content[0].text.strip()
        print(f"[OK] Claude Haiku responded: '{reply}'")
        return True
    except Exception as error:  # noqa: BLE001 — surfacing any provider error is the point here
        print(f"[FAIL] Could not reach Claude: {error}")
        return False


def main() -> None:
    """Runs all verification checks and exits non-zero on any failure."""
    load_dotenv()

    checks = [
        check_adk_cli_installed(),
        check_required_env_vars(),
        check_claude_connectivity(),
    ]

    if all(checks):
        print("\nEnvironment is ready. Move on to Lesson 2.")
    else:
        print("\nFix the failures above before continuing.")
        sys.exit(1)


if __name__ == "__main__":
    main()
