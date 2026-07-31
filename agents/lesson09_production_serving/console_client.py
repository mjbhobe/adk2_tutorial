"""Lesson 9: Console client for the relationship manager agent's API.

A second, minimal illustration of calling the same API endpoint the
Streamlit app uses, this time from a plain command-line script.
Run this alongside main.py in a separate terminal.

Run with:
    uv run agents/lesson09_production_serving/console_client.py
"""

import uuid

import requests

API_URL = "http://127.0.0.1:8080/chat"


def main() -> None:
    """Runs a command-line chat loop against the agent's API."""
    user_id = f"console-user-{uuid.uuid4().hex[:8]}"
    session_id = f"console-session-{uuid.uuid4().hex[:8]}"

    print("Relationship Manager Assistant (console client)")
    print("Type 'exit' to quit.\n")

    while True:
        message = input("You: ").strip()
        if message.lower() in {"exit", "quit"}:
            break
        if not message:
            continue

        response = requests.post(
            API_URL,
            json={"user_id": user_id, "session_id": session_id, "message": message},
            timeout=60,
        )
        response.raise_for_status()
        print(f"Agent: {response.json()['response']}\n")


if __name__ == "__main__":
    main()

