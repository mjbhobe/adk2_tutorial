"""
KYC field tracking for the account onboarding agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from google.adk.tools import ToolContext

REQUIRED_KYC_FIELDS = [
    "full_name",
    "date_of_birth",
    "residential_address",
    "id_type",
    "id_number",
    "employment_status",
    "source_of_funds",
]


def record_kyc_detail(
    tool_context: ToolContext,
    field_name: str,
    field_value: str,
) -> dict:
    """Records one KYC field for the customer currently being onboarded.

    Args:
        tool_context: Injected automatically by ADK; gives access to
            the current session's state.
        field_name: Which KYC field this is. Must be one of:
            full_name, date_of_birth, residential_address, id_type,
            id_number, employment_status, source_of_funds.
        field_value: The value the customer provided for this field.

    Returns:
        A dict confirming what was recorded, everything collected so
        far, and which required fields are still missing.
    """
    if field_name not in REQUIRED_KYC_FIELDS:
        return {
            "error": (
                f"Unknown field '{field_name}'. Valid fields are: "
                f"{', '.join(REQUIRED_KYC_FIELDS)}"
            )
        }

    kyc_data = tool_context.state.get("kyc_data", {})
    kyc_data[field_name] = field_value
    tool_context.state["kyc_data"] = kyc_data

    missing = [f for f in REQUIRED_KYC_FIELDS if f not in kyc_data]
    is_complete = not missing
    tool_context.state["kyc_status"] = (
        "All required KYC fields collected."
        if is_complete
        else f"Still missing: {', '.join(missing)}"
    )

    return {
        "recorded_field": field_name,
        "kyc_data_so_far": kyc_data,
        "missing_fields": missing,
        "is_complete": is_complete,
    }
