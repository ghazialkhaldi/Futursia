# Getting stock prices from Yahoo Finance.

import time
from datetime import datetime, timezone

import requests

# Remember recent Yahoo answers for a few seconds so that many page refreshes
# don't turn into many requests to Yahoo.
# Each entry looks like: url -> (time it was saved, Yahoo's answer)
cache = {}


def get_chart(symbol, range_, interval, max_age_seconds):
    """Download price data for one stock.

    range_ is how far back to go, like "1d" (one day) or "5d" (five days).
    interval is the size of each bar, like "1m" (one minute) or "1d" (one day).
    """
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + symbol
        + "?range=" + range_
        + "&interval=" + interval
    )

    if url in cache:
        saved_time, saved_chart = cache[url]
        if time.time() - saved_time < max_age_seconds:
            return saved_chart

    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    if response.status_code != 200:
        raise Exception("Yahoo returned " + str(response.status_code) + " for " + symbol)

    results = response.json()["chart"]["result"]
    if not results:
        raise Exception("No data for " + symbol)
    chart = results[0]

    cache[url] = (time.time(), chart)
    return chart


def get_bars(chart):
    """Turn Yahoo's price lists into a list of bars.

    Yahoo sends separate lists (all the opens, all the closes, ...).
    We turn them into one list like:
    [{"time": ..., "open": ..., "high": ..., "low": ..., "close": ...}, ...]
    """
    times = chart.get("timestamp", [])
    prices = chart["indicators"]["quote"][0]
    bars = []

    for i in range(len(times)):
        bar = {
            "time": datetime.fromtimestamp(times[i], timezone.utc).isoformat(),
            "open": prices["open"][i],
            "high": prices["high"][i],
            "low": prices["low"][i],
            "close": prices["close"][i],
        }
        # Yahoo sometimes leaves gaps (None) when no trade happened that minute.
        if bar["open"] and bar["high"] and bar["low"] and bar["close"]:
            bars.append(bar)

    return bars


def get_quote(chart):
    """Current price and today's change. Yahoo puts these in chart["meta"]."""
    meta = chart["meta"]
    price = meta["regularMarketPrice"]
    previous_close = meta.get("previousClose") or meta["chartPreviousClose"]
    change = price - previous_close

    return {
        "price": price,
        "previous_close": previous_close,
        "change": change,
        "change_percent": change / previous_close * 100,
        "high": meta.get("regularMarketDayHigh"),
        "low": meta.get("regularMarketDayLow"),
    }


def is_market_open(chart):
    """Yahoo tells us when today's regular trading session starts and ends."""
    session = chart["meta"]["currentTradingPeriod"]["regular"]
    now = time.time()
    return session["start"] <= now < session["end"]


def get_session_times(chart):
    """Opening and closing time of the regular trading session, in UTC."""
    session = chart["meta"]["currentTradingPeriod"]["regular"]
    session_open = datetime.fromtimestamp(session["start"], timezone.utc)
    session_close = datetime.fromtimestamp(session["end"], timezone.utc)
    return session_open, session_close
