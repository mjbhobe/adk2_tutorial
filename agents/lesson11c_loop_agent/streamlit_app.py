"""Lesson 11c: Streamlit front-end for document verification.

Collects the applicant's name and Aadhaar number, assembles them into
the sentence-shaped text the agent expects, and sends that to the API's
/verify-document endpoint. The retry loop runs entirely inside that one
request, this form only ever sees the final result.

Run this alongside api.py in a separate terminal, not instead of it.

Run with:
    streamlit run agents/lesson11c_loop_agent/streamlit_app.py
"""

import uuid

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8082/verify-document"

st.set_page_config(page_title="Document Verification", page_icon="📄")
st.title("KYC Document Verification")
st.caption(
    "A dummy front-end standing in for a real onboarding screen. "
    "It knows nothing about ADK; it only talks to our pipeline's API."
)

if "user_id" not in st.session_state:
    st.session_state.user_id = f"streamlit-user-{uuid.uuid4().hex[:8]}"

with st.form("document_check"):
    applicant_name = st.text_input("Full name")
    aadhaar_number = st.text_input("Aadhaar number (12 digits)")
    submitted = st.form_submit_button("Verify document")

if submitted:
    application_text = (
        f"Verify the Aadhaar document for {applicant_name}, "
        f"Aadhaar number {aadhaar_number}."
    )

    with st.spinner("Verifying, retrying automatically if needed..."):
        response = requests.post(
            API_URL,
            json={
                "user_id": st.session_state.user_id,
                "session_id": f"session-{uuid.uuid4().hex[:8]}",
                "application_text": application_text,
            },
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()["result"]

    if result["passed"]:
        st.success(f"Verified after {result['attempt_number']} attempt(s).")
    else:
        st.error(f"Verification failed after {result['attempt_number']} attempt(s). Referred to manual review.")
        if result.get("issue"):
            st.write(f"Last issue: {result['issue']}")

    st.json(result)
