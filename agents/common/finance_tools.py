"""
Shared market-data tools for BFSI investment research agents.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""

import os

import yfinance as yf
from tavily import TavilyClient


def get_stock_price(ticker: str) -> dict:
    """Fetches the latest closing price and day-over-day change for a stock.

    Args:
        ticker: The stock ticker symbol, using Yahoo Finance conventions.
            Examples: "AAPL" for Apple (US), "RELIANCE.NS" for Reliance
            Industries (India, NSE), "SAP.DE" for SAP (Germany, Xetra).

    Returns:
        A dict with the latest close price, previous close, percent
        change, currency, and the company name, or an error message
        if the ticker could not be found.
    """
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period="5d")

        if history.empty:
            return {
                "found": False,
                "ticker": ticker,
                "error": (
                    f"No price data found for this ticker ({ticker})."
                    f"Check the symbol and, for non-US exchanges, the suffix "
                    f"(e.g. .NS for India, .DE for Germany)."
                ),
            }

        latest = history.iloc[-1]
        previous = history.iloc[-2] if len(history) > 1 else latest
        latest_close = float(latest["Close"])
        previous_close = float(previous["Close"])
        change_percent = (
            ((latest_close - previous_close) / previous_close) * 100
            if previous_close
            else 0.0
        )

        company_name = ticker
        currency = ""
        try:
            info = stock.info
            company_name = info.get("longName") or info.get("shortName") or ticker
            currency = info.get("currency", "")
        except Exception:
            pass

        return {
            "found": True,
            "ticker": ticker,
            "company_name": company_name,
            "latest_close": round(latest_close, 2),
            "previous_close": round(previous_close, 2),
            "change_percent": round(change_percent, 2),
            "currency": currency,
            "as_of_date": str(latest.name.date()),
        }
    except Exception as error:
        return {"found": False, "ticker": ticker, "error": str(error)}


def get_stock_news(company_or_ticker: str, max_results: int = 5) -> dict:
    """Searches the web for recent news about a company or stock.

    This is a provider-agnostic alternative to ADK's built-in
    google_search tool. It works with any model, including Claude,
    since it's a plain function tool rather than a model built-in.
    Uses Tavily, a search API purpose-built for AI agents, with its
    finance-specific search mode for more relevant results.

    Args:
        company_or_ticker: The company name or ticker symbol to search
            news for, e.g. "Tata Motors" or "TSLA".
        max_results: Maximum number of news results to return.
            Defaults to 5.

    Returns:
        A dict with a list of articles, each containing a title,
        short snippet, and source URL.
    """
    try:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return {
                "found": False,
                "query": company_or_ticker,
                "error": "TAVILY_API_KEY is not set in the environment.",
            }

        client = TavilyClient(api_key=api_key)
        query = f"{company_or_ticker} stock news"
        response = client.search(
            query=query,
            max_results=max_results,
            topic="finance",
        )

        articles = [
            {
                "title": r.get("title", ""),
                "snippet": r.get("content", ""),
                "url": r.get("url", ""),
            }
            for r in response.get("results", [])
        ]
        return {"found": bool(articles), "query": query, "articles": articles}
    except Exception as error:
        return {"found": False, "query": company_or_ticker, "error": str(error)}
