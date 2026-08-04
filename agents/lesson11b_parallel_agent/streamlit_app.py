"""Lesson 11b: Streamlit front-end for the KYC onboarding pipeline.

Collects the application as separate form fields, then assembles them
into one sentence and sends that to the API's /kyc-check endpoint. The
three checks still run independently from that same text, and the
decision agent still merges them, the form just gives whoever's
onboarding the customer a friendlier way to provide the information
than typing free text.

Run this alongside api.py in a separate terminal, not instead of it.

Run with:
    streamlit run agents/lesson11b_parallel_agent/streamlit_app.py
"""

import uuid

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8081/kyc-check"

st.set_page_config(page_title="KYC Onboarding", page_icon="🪪")
st.title("New Customer KYC Onboarding")
st.caption(
    "A dummy front-end standing in for a real onboarding screen. "
    "It knows nothing about ADK; it only talks to our pipeline's API."
)

if "user_id" not in st.session_state:
    st.session_state.user_id = f"streamlit-user-{uuid.uuid4().hex[:8]}"

with st.form("kyc_application"):
    applicant_name = st.text_input("Full name")
    pan_number = st.text_input("PAN")
    date_of_birth = st.date_input("Date of birth")
    aadhaar_number = st.text_input("Aadhaar number (12 digits)")
    submitted = st.form_submit_button("Run KYC checks")

if submitted:
    application_text = (
        f"New customer KYC application: {applicant_name}, PAN {pan_number}, "
        f"date of birth {date_of_birth.isoformat()}, Aadhaar number {aadhaar_number}."
    )

    with st.spinner("Running credit bureau, fraud watchlist, and document checks..."):
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
        result = response.json()

    decision = result["decision"]
    if decision["decision"] == "approved":
        st.success("Approved")
    elif decision["decision"] == "manual_review":
        st.warning("Referred to manual review")
    else:
        st.error("Rejected")

    st.write("Reasons:")
    for reason in decision["reasons"]:
        st.write(f"- {reason}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Credit bureau")
        st.json(result["credit_bureau"])

    with col2:
        st.subheader("Fraud watchlist")
        fraud = result["fraud_watchlist"]
        if fraud["is_flagged"]:
            st.error(f"Flagged: {fraud['watchlist_type']}")
        else:
            st.success("Clear")
        st.json(fraud)

    with col3:
        st.subheader("KYC documents")
        docs = result["kyc_document"]
        if docs["aadhaar_valid_format"] and docs["documents_match"]:
            st.success("Verified")
        else:
            st.error("Verification failed")
        st.json(docs)
