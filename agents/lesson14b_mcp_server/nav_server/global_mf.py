"""Lesson 14b: Real global mutual fund data via yfinance.

Covers non-Indian funds, identified by ticker rather than an AMFI
scheme code, e.g. VFIAX for Vanguard 500 Index Fund Admiral Shares.
yfinance itself is synchronous, so calls run in a thread via
asyncio.to_thread, keeping this an async tool without blocking the
server's event loop.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import asyncio

import yfinance as yf


def _fetch_latest_price(ticker: str) -> dict | None:
    history = yf.Ticker(ticker).history(period="5d")
    if history.empty:
        return None
    last_row = history.iloc[-1]
    return {
        "ticker": ticker.upper(),
        "price": round(float(last_row["Close"]), 4),
        "date": history.index[-1].strftime("%Y-%m-%d"),
        "currency": "USD",
    }


def _fetch_price_history(ticker: str, days: int) -> dict | None:
    history = yf.Ticker(ticker).history(period=f"{max(days, 5)}d")
    if history.empty:
        return None
    recent = history.tail(days)
    entries = [
        {"date": idx.strftime("%Y-%m-%d"), "price": round(float(row["Close"]), 4)}
        for idx, row in recent.iterrows()
    ]
    return {"ticker": ticker.upper(), "currency": "USD", "history": list(reversed(entries))}


async def get_global_mf_price(ticker: str) -> dict:
    """Fetches the latest price for a global (e.g. US) mutual fund.

    Args:
        ticker: The fund's ticker symbol, e.g. "VFIAX". Not for Indian
            mutual funds, use get_indian_mf_nav for those.

    Returns:
        A dict with ticker, price, date, and currency ("USD"), or an
        error field if the ticker isn't found.
    """
    result = await asyncio.to_thread(_fetch_latest_price, ticker)
    if result is None:
        return {"error": f"Could not find ticker: {ticker}"}
    return result


async def get_global_mf_price_history(ticker: str, days: int) -> dict:
    """Fetches recent price history for a global (e.g. US) mutual fund.

    Args:
        ticker: The fund's ticker symbol, e.g. "VFIAX".
        days: How many most recent days of history to return.

    Returns:
        A dict with ticker, currency, and history, a list of
        {date, price} entries, most recent first. Error field if the
        ticker isn't found.
    """
    result = await asyncio.to_thread(_fetch_price_history, ticker, days)
    if result is None:
        return {"error": f"Could not find ticker: {ticker}"}
    return result
