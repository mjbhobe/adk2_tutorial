"""Lesson 14b: Real Indian mutual fund data via api.mfapi.in.

api.mfapi.in is a free, unauthenticated wrapper around AMFI's own daily
NAV feed. No API key, no signup.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

from datetime import datetime

import httpx

BASE_URL = "https://api.mfapi.in/mf"


async def search_indian_mf_schemes(query: str) -> list[dict]:
    """Searches Indian mutual fund schemes by name.

    Args:
        query: Text to search for, e.g. "HDFC Flexi Cap" or "SBI Bluechip".

    Returns:
        A list of matching schemes, each with scheme_code and
        scheme_name, capped at 10 results.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{BASE_URL}/search", params={"q": query})
        response.raise_for_status()
        results = response.json()

    return [
        {"scheme_code": str(r["schemeCode"]), "scheme_name": r["schemeName"]}
        for r in results[:10]
    ]


async def get_indian_mf_nav(scheme_code: str) -> dict:
    """Fetches the latest NAV for an Indian mutual fund scheme.

    Args:
        scheme_code: The AMFI scheme code, e.g. "119551". Use
            search_indian_mf_schemes first if you only have a fund name.

    Returns:
        A dict with scheme_code, scheme_name, nav, date, and currency
        ("INR"), or an error field if the scheme code isn't found.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{BASE_URL}/{scheme_code}/latest")

    if response.status_code != 200:
        return {"error": f"Could not find scheme_code: {scheme_code}"}

    data = response.json()
    entries = data.get("data", [])
    if not entries:
        return {"error": f"No NAV data available for scheme_code: {scheme_code}"}

    meta = data.get("meta", {})
    latest = entries[0]
    return {
        "scheme_code": scheme_code,
        "scheme_name": meta.get("scheme_name", ""),
        "nav": float(latest["nav"]),
        "date": latest["date"],
        "currency": "INR",
    }


async def get_indian_mf_nav_history(scheme_code: str, days: int) -> dict:
    """Fetches recent NAV history for an Indian mutual fund scheme.

    Args:
        scheme_code: The AMFI scheme code, e.g. "119551".
        days: How many most recent days of history to return.

    Returns:
        A dict with scheme_code, scheme_name, currency, and history, a
        list of {date, nav} entries, most recent first. Error field if
        the scheme code isn't found.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{BASE_URL}/{scheme_code}")

    if response.status_code != 200:
        return {"error": f"Could not find scheme_code: {scheme_code}"}

    data = response.json()
    entries = data.get("data", [])
    if not entries:
        return {"error": f"No NAV data available for scheme_code: {scheme_code}"}

    # api.mfapi.in returns the entire history; sort explicitly rather than
    # assume its ordering, then take the most recent `days` entries.
    parsed = [
        {"date_obj": datetime.strptime(e["date"], "%d-%m-%Y"), "date": e["date"], "nav": float(e["nav"])}
        for e in entries
    ]
    parsed.sort(key=lambda e: e["date_obj"], reverse=True)
    recent = parsed[:days]

    meta = data.get("meta", {})
    return {
        "scheme_code": scheme_code,
        "scheme_name": meta.get("scheme_name", ""),
        "currency": "INR",
        "history": [{"date": e["date"], "nav": e["nav"]} for e in recent],
    }
