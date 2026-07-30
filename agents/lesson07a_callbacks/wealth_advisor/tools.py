"""Lesson 7a: Callbacks in Practice.

Tool functions for the wealth management advisory agent. These are
plain Python functions with no ADK dependency, exactly like every
tool in this series, kept separate from agent.py so they can be
read, tested, and reasoned about independently.

@author: Manish Bhobé
My experiments with Python, Agentic AI and ADK.
Code shared for learning purposes only! Use at your own risk.
No warranties or guarantees of any kind.
"""


def get_portfolio_summary(customer_id: str) -> dict:
    """Returns a portfolio summary for the given customer.

    In a real system this would query the bank's portfolio management
    platform. Here we return realistic mock data so the lesson works
    without any external dependencies.

    Args:
        customer_id: The bank's unique identifier for this customer.

    Returns:
        A dict with total portfolio value, currency, and allocation
        breakdown across asset classes.
    """
    portfolios = {
        "CUST001": {
            "customer_id": "CUST001",
            "total_value": 12500000,
            "currency": "INR",
            "segments": {"equity": 60, "debt": 30, "liquid": 10},
        },
        "CUST002": {
            "customer_id": "CUST002",
            "total_value": 4200000,
            "currency": "INR",
            "segments": {"equity": 45, "debt": 45, "liquid": 10},
        },
    }
    return portfolios.get(
        customer_id,
        {
            "found": False,
            "customer_id": customer_id,
            "error": "Customer ID not found in portfolio system.",
        },
    )


def get_market_indices(markets: str = "IN,US,EU") -> dict:
    """Returns current market index levels for the requested markets.

    Fetches live closing prices from Yahoo Finance using index ticker
    symbols. Falls back to a clear error message per index if a fetch
    fails, rather than crashing the whole tool call.

    Args:
        markets: Comma-separated market codes. Supported: IN, US, EU.
            Defaults to all three.

    Returns:
        A dict of index names to their latest closing levels, plus a
        status field indicating whether markets are currently open.
    """
    import yfinance as yf

    index_map = {
        "IN": {"BSE_SENSEX": "^BSESN", "NSE_NIFTY50": "^NSEI"},
        "US": {"SP500": "^GSPC", "NASDAQ": "^IXIC"},
        "EU": {"FTSE100": "^FTSE", "DAX": "^GDAXI"},
    }

    result = {}
    for code in markets.split(","):
        code = code.strip().upper()
        if code not in index_map:
            result[code] = "Unknown market code"
            continue
        for name, ticker_symbol in index_map[code].items():
            try:
                ticker = yf.Ticker(ticker_symbol)
                hist = ticker.history(period="2d")
                if hist.empty:
                    result[name] = "No data available"
                else:
                    result[name] = round(float(hist["Close"].iloc[-1]), 2)
            except Exception as e:
                result[name] = f"Fetch error: {str(e)}"

    result["status"] = "live_data"
    return result
