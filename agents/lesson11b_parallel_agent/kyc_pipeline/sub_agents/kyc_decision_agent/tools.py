"""Lesson 11b: Tools for the KYC decision agent.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

# How many recent hard enquiries are tolerated before flagging for manual
# review. In production this threshold would come from the same kind of
# risk policy configuration as Lesson 11a's rate cards, not a constant.
MAX_RECENT_ENQUIRIES = 3


def make_kyc_decision(
    is_flagged: bool,
    watchlist_type: str | None,
    aadhaar_valid_format: bool,
    documents_match: bool,
    has_defaults: bool,
    recent_enquiries_count: int,
) -> dict:
    """Applies the onboarding decision rules to the three parallel checks' results.

    Rules, applied in order:
        1. A watchlist hit is an automatic rejection, no exceptions.
        2. A document problem (bad format or no match) sends the case to
           manual review, it could just as easily be a data entry error
           as actual fraud, so a human should look before rejecting.
        3. A prior default sends the case to manual review.
        4. Unusually high recent credit enquiries sends the case to
           manual review, a standard "credit hungry" risk signal.
        5. If none of the above apply, the application is approved.

    Args:
        is_flagged: Whether the applicant matched a sanctions or PEP watchlist.
        watchlist_type: "PEP" or "Sanctions List", if flagged.
        aadhaar_valid_format: Whether the Aadhaar number passed format validation.
        documents_match: Whether the mock records check found a match.
        has_defaults: Whether the credit bureau report shows a prior default.
        recent_enquiries_count: Number of hard credit enquiries in the last 6 months.

    Returns:
        A dict with:
            decision (str): One of "approved", "manual_review", "rejected".
            reasons (list[str]): Every rule that contributed to the decision.
    """
    if is_flagged:
        return {
            "decision": "rejected",
            "reasons": [f"Flagged on watchlist: {watchlist_type}"],
        }

    reasons = []
    if not aadhaar_valid_format or not documents_match:
        reasons.append("KYC document verification failed")
    if has_defaults:
        reasons.append("Prior default on credit bureau record")
    if recent_enquiries_count > MAX_RECENT_ENQUIRIES:
        reasons.append(f"High recent credit enquiries ({recent_enquiries_count})")

    if reasons:
        return {"decision": "manual_review", "reasons": reasons}

    return {"decision": "approved", "reasons": ["All checks cleared"]}
