"""Lesson 12: Tools for the disbursement agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import io

from google.adk.tools import ToolContext
from google.genai import types
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


async def generate_loan_offer_letter(
    tool_context: ToolContext,
    applicant_name: str,
    loan_amount: float,
    tenure_months: int,
    interest_rate: float,
) -> dict:
    """Generates a loan offer letter as a PDF and saves it as an artifact.

    Uses the Lesson 6c artifact pattern, tool_context.save_artifact, to
    persist the generated file against this session.

    Args:
        tool_context: Supplied automatically by ADK.
        applicant_name: The approved applicant's full name.
        loan_amount: The approved loan amount, in INR.
        tenure_months: The loan tenure, in months.
        interest_rate: The annual interest rate, as a percentage.

    Returns:
        A dict with:
            artifact_filename (str): The saved PDF's filename.
            artifact_version (int): The version ADK assigned it.
    """
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(72, 740, "Loan Offer Letter")

    pdf.setFont("Helvetica", 11)
    lines = [
        f"Dear {applicant_name},",
        "",
        "We are pleased to offer you the following loan, subject to the",
        "terms and conditions set out in your formal loan agreement.",
        "",
        f"Loan amount: INR {loan_amount:,.0f}",
        f"Tenure: {tenure_months} months",
        f"Interest rate: {interest_rate}% per annum",
        "",
        "This letter is generated for demonstration purposes as part of",
        "an ADK tutorial and is not a real financial instrument.",
    ]
    y = 700
    for line in lines:
        pdf.drawString(72, y, line)
        y -= 20

    pdf.save()
    pdf_bytes = buffer.getvalue()

    filename = f"loan_offer_{applicant_name.replace(' ', '_')}.pdf"
    artifact_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    version = await tool_context.save_artifact(
        filename=filename, artifact=artifact_part
    )

    result = {"artifact_filename": filename, "artifact_version": version}
    tool_context.state["disbursement_result"] = result
    return result
