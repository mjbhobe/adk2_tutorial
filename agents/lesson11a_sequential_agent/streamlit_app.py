"""Lesson 11a: Streamlit front-end for the loan underwriting pipeline.

Collects the application as separate form fields, matching what a real
loan officer's intake screen would look like, then assembles them into
one sentence and sends that to the API's /apply endpoint. The intake
agent still does its job unchanged: extracting fields and validating
the PAN. This form just gives the applicant a friendlier way to provide
that same information than typing free text.

Run this alongside api.py in a separate terminal, not instead of it.

Run with:
    streamlit run agents/lesson11a_sequential_agent/streamlit_app.py
"""

import uuid

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8080/apply"

st.set_page_config(page_title="Loan Application", page_icon="🏦")
st.title("Loan Application")
st.caption(
    "A dummy front-end standing in for a real loan origination screen. "
    "It knows nothing about ADK; it only talks to our pipeline's API."
)

if "user_id" not in st.session_state:
    st.session_state.user_id = f"streamlit-user-{uuid.uuid4().hex[:8]}"

with st.form("loan_application"):
    applicant_name = st.text_input("Full name")
    pan_number = st.text_input("PAN")
    loan_type = st.selectbox("Loan type", ["home", "car", "personal"])
    loan_amount = st.number_input("Loan amount (INR)", min_value=1.0, step=10000.0)
    tenure_months = st.number_input("Tenure (months)", min_value=1, step=1)
    annual_income = st.number_input("Annual income (INR)", min_value=1.0, step=10000.0)
    purpose = st.text_input("Purpose of the loan")
    submitted = st.form_submit_button("Submit application")

if submitted:
    # The intake agent still expects free text, so we assemble the form
    # fields into a sentence rather than changing the pipeline's contract.
    application_text = (
        f"{applicant_name} wants a {loan_type} loan of INR {loan_amount:.0f} "
        f"over {int(tenure_months)} months for {purpose}. "
        f"PAN is {pan_number} and annual income is INR {annual_income:.0f}."
    )

    with st.spinner("Running the pipeline..."):
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
        st.success(f"Approved at {decision['interest_rate']}% p.a.")
    elif decision["decision"] == "rejected":
        st.error("Rejected")
    else:
        st.warning("Referred to a human underwriter")

    st.write("Reasons:")
    for reason in decision["reasons"]:
        st.write(f"- {reason}")

    with st.expander("See every step's result"):
        st.json(result)
