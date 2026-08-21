"""Lesson 15a: See the raw A2A task lifecycle underneath RemoteA2aAgent.

RemoteA2aAgent handles all of this for you, submitting a task, polling
it, resolving the final state. This script skips RemoteA2aAgent
entirely and talks to the server's own protocol endpoint directly, so
you can see the actual task object A2A passes around, not just the
final answer.

Start risk_service.py first, in a separate terminal, before
running this.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import asyncio
import json

import httpx


async def main() -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8001/",
            json={
                "jsonrpc": "2.0",
                "id": "req-1",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": "credit score 773, annual income 900000, loan amount 500000, tenure 36 months, no defaults"}],
                        "messageId": "msg-1",
                    }
                },
            },
        )
        result = response.json()
        task = result["result"]
        print("Task ID:", task["id"])
        print("Task state:", task["status"]["state"])
        print()
        print("Full task object:")
        print(json.dumps(task, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
