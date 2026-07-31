"""Lesson 9: Streamlit front-end for the relationship manager agent.

Stands in for a real production portal that would call our agent's
API rather than embedding ADK directly. Run this alongside main.py
in a separate terminal, not instead of it.

Run with:
    streamlit run agents/lesson09_production_serving/streamlit_app.py
"""

import uuid

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8080/chat"

st.set_page_config(page_title="Wealth Management Assistant", page_icon="💬")
st.title("Wealth Management Assistant")
st.caption(
    "This is a dummy front-end standing in for a real banking portal. "
    "It knows nothing about ADK; it only talks to our agent's API."
)

# Generate stable IDs for this browser tab on first load.
if "user_id" not in st.session_state:
    st.session_state.user_id = f"streamlit-user-{uuid.uuid4().hex[:8]}"
if "session_id" not in st.session_state:
    st.session_state.session_id = f"streamlit-session-{uuid.uuid4().hex[:8]}"
if "messages" not in st.session_state:
    st.session_state.messages = []

for role, text in st.session_state.messages:
    with st.chat_message(role):
        st.write(text)

user_input = st.chat_input("Ask about your portfolio...")

if user_input:
    st.session_state.messages.append(("user", user_input))

    """
    NOTE:
    st.chat_message() is a Streamlit built-in component that renders a chat bubble with an avatar. 
    The string you pass to it is the role name, and Streamlit recognises two special values:

    "user" — renders a human avatar (a person icon) on the right side of the chat bubble
    "assistant" — renders a bot/robot avatar on the left side

    These are Streamlit's own conventions, completely unrelated to ADK. Streamlit picked "user" and "assistant" because those are the standard role names used across virtually every LLM API (OpenAI, Anthropic, Google), so it made sense to align with that vocabulary. If you pass any other string — say "system" or "bank" — Streamlit will still render a bubble, but with a generic icon rather than the human or robot avatar.
    """
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = requests.post(
                API_URL,
                json={
                    "user_id": st.session_state.user_id,
                    "session_id": st.session_state.session_id,
                    "message": user_input,
                },
                timeout=60,
            )
            response.raise_for_status()
            reply_text = response.json()["response"]
        st.write(reply_text)

    st.session_state.messages.append(("assistant", reply_text))
