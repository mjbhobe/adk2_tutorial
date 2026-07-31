"""Lesson 6c: Artifacts — loan summary PDF tool.

This tool is async because tool_context.save_artifact() is an async
method. ADK supports async tool functions natively — the only change
from a regular tool is the `async def` and `await` keyword.
"""

import io

from google.adk.tools import ToolContext
from google.genai import types
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


async def calculate_loan_summary(
    tool_context: ToolContext,
    applicant_name: str,
    principal: float,
    annual_interest_rate_percent: float,
    tenure_months: int,
) -> dict:
    """Calculates loan figures and saves a PDF summary report as an artifact.

    Args:
        tool_context: Injected by ADK; required to save the PDF artifact.
        applicant_name: Full name of the loan applicant.
        principal: Loan amount in INR.
        annual_interest_rate_percent: Annual interest rate as a percentage.
        tenure_months: Loan tenure in months.

    Returns:
        A dict with the calculated figures and the artifact filename and
        version number assigned by the artifact service.
    """
    monthly_rate = (annual_interest_rate_percent / 100) / 12
    growth_factor = (1 + monthly_rate) ** tenure_months
    emi = principal * monthly_rate * growth_factor / (growth_factor - 1)
    total_payment = emi * tenure_months
    total_interest = total_payment - principal

    # Build the PDF in memory using reportlab.
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    _, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, height - 72, "Loan Summary Report")

    y = height - 120
    rows = [
        ("Applicant", applicant_name),
        ("Loan Amount", f"INR {principal:,.2f}"),
        ("Annual Interest Rate", f"{annual_interest_rate_percent}%"),
        ("Tenure", f"{tenure_months} months ({tenure_months // 12} years)"),
        ("Monthly EMI", f"INR {emi:,.2f}"),
        ("Total Interest Payable", f"INR {total_interest:,.2f}"),
        ("Total Amount Payable", f"INR {total_payment:,.2f}"),
    ]
    for label, value in rows:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, y, f"{label}:")
        c.setFont("Helvetica", 11)
        c.drawString(240, y, value)
        y -= 26

    c.save()
    pdf_bytes = buffer.getvalue()

    # Wrap the raw bytes in a types.Part — ADK's standard container for
    # binary data, carrying both the bytes and the MIME type together.
    filename = f"loan_summary_{applicant_name.replace(' ', '_')}.pdf"
    artifact = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")

    # save_artifact is async — hence `await` and `async def` on this function.
    # It returns a version number; version 0 is the first save, 1 the second, etc.
    version = await tool_context.save_artifact(filename=filename, artifact=artifact)

    return {
        "applicant_name": applicant_name,
        "monthly_emi": round(emi, 2),
        "total_interest": round(total_interest, 2),
        "total_payment": round(total_payment, 2),
        "artifact_filename": filename,
        "artifact_version": version,
    }
