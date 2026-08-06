"""Lesson 12: Streamlit front-end for the loan approval pipeline.

Two forms, not one. Submitting the first calls /apply and shows the
credit and risk findings, exactly what the console version prints.
Choosing a decision and submitting the second calls /officer-decision,
resuming the same paused application by session_id. This is the same
two-call pattern main.py's console loop uses, just spread across two
separate page interactions instead of two console prompts.

Run this alongside api.py in a separate terminal, not instead of it.

Run with:
    streamlit run agents/lesson12_human_in_the_loop/streamlit_app.py
"""

import uuid

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8083"

st.set_page_config(page_title="Loan Approval", page_icon="🏦")
st.title("Loan Approval Pipeline")
st.caption(
    "A dummy front-end standing in for a loan officer's review screen. "
    "It knows nothing about ADK; it only talks to our pipeline's API."
)

if "user_id" not in st.session_state:
    st.session_state.user_id = f"streamlit-user-{uuid.uuid4().hex[:8]}"
if "pending_session_id" not in st.session_state:
    st.session_state.pending_session_id = None
if "pending_result" not in st.session_state:
    st.session_state.pending_result = None

# Once an application is pending, show the officer's review form instead
# of the application form, until a decision is submitted.
if st.session_state.pending_session_id is None:
    with st.form("loan_application"):
        application_text = st.text_area(
            "Loan application",
            placeholder="Rohan Mehta wants a personal loan of INR 500000 over 36 months. "
            "PAN is ROHAN1234M, annual income is INR 900000.",
        )
        submitted = st.form_submit_button("Submit application")

    if submitted and application_text.strip():
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        with st.spinner("Running credit check and risk scoring..."):
            response = requests.post(
                f"{API_URL}/apply",
                json={
                    "user_id": st.session_state.user_id,
                    "session_id": session_id,
                    "application_text": application_text,
                },
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()

        st.session_state.pending_session_id = session_id
        st.session_state.pending_result = result
        st.rerun()

else:
    result = st.session_state.pending_result
    st.subheader("Pending officer review")
    st.write("Credit result:")
    st.json(result["credit_result"])
    st.write("Risk result:")
    st.json(result["risk_result"])

    decision = st.radio("Decision", ["APPROVE", "REJECT", "REFER"], horizontal=True)
    if st.button("Submit decision"):
        with st.spinner("Resuming the pipeline with your decision..."):
            response = requests.post(
                f"{API_URL}/officer-decision",
                json={
                    "user_id": st.session_state.user_id,
                    "session_id": st.session_state.pending_session_id,
                    "decision": decision,
                },
                timeout=60,
            )
            response.raise_for_status()
            outcome = response.json()

        st.success(f"Decision recorded: {outcome['officer_decision']}")
        if outcome.get("referral_task"):
            st.write("Referral task created:")
            st.json(outcome["referral_task"])
        st.json(outcome)

        # Reset for the next application.
        st.session_state.pending_session_id = None
        st.session_state.pending_result = None
