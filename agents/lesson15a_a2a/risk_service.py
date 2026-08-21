"""Lesson 15a: Serve risk_specialist_agent over A2A.

Run this file directly, it's a standalone server, not something
adk web or another agent's main.py imports.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))  # adds agents/ for common.*
sys.path.insert(0, str(THIS_DIR))  # adds this lesson's own folder for risk_specialist.*

from google.adk.a2a.utils.agent_to_a2a import to_a2a

from risk_specialist.agent import risk_specialist_agent

app = to_a2a(risk_specialist_agent, host="localhost", port=8001)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
