# The 3-hour forecast.
#
# Idea: over the next 3 hours, a stock tends to drift back toward its
# average price for the day. If it's trading above today's average we lean
# DOWN, if below we lean UP. If it's very close to the average, FLAT.
#
# How well does it work? Only a little better than a coin flip:
# - On 60 days of 5-minute data for all 90 stocks: right 52-54% of the time.
# - On 2 years of hourly data: right 50.6% of the time.
# So treat it as a small lean, not a prediction you can count on.
#
# We also tested days, weeks and months ahead. Over those, the only thing
# that could be predicted was that stocks in general tend to rise, so every
# stock would just say UP.

import random
from datetime import datetime, timedelta

FORECAST_MINUTES = 3 * 60  # 3 hours


def make_forecast(bars):
    if len(bars) == 0:
        return {"direction": "FLAT", "return_percent": 0, "target_price": None,
                "average_price": None, "difference_percent": 0}

    # Only use bars from the most recent trading day.
    # The first 10 characters of the time are the date, like "2026-09-30".
    last_day = bars[-1]["time"][:10]
    today_bars = [bar for bar in bars if bar["time"][:10] == last_day]

    price = today_bars[-1]["close"]
    total = 0
    for bar in today_bars:
        total += bar["close"]
    average = total / len(today_bars)

    # How far the price is from today's average, in percent.
    # Negative = price is below the average, positive = above.
    difference_percent = (price - average) / average * 100

    # Expect the price to move back about 8% of the way toward the average
    # in 3 hours. (0.08 is the best fit from the test data.)
    return_percent = -difference_percent * 0.08

    # Within 0.1% of the average there's no signal, so we say FLAT.
    direction = "FLAT"
    if difference_percent <= -0.1:
        direction = "UP"
    if difference_percent >= 0.1:
        direction = "DOWN"

    return {
        "direction": direction,
        "return_percent": return_percent,
        "target_price": price * (1 + return_percent / 100),
        "average_price": average,
        "difference_percent": difference_percent,
    }


def next_trading_minute(time, session_open, session_close):
    """The next minute the market is open, skipping nights and weekends.

    session_open and session_close are the opening and closing times of a
    trading day (in UTC). Only their time of day is used.
    """
    time = time + timedelta(minutes=1)

    # After the close: jump to the next morning's open.
    if time.time() >= session_close.time():
        time = time + timedelta(days=1)
        time = time.replace(hour=session_open.hour, minute=session_open.minute)

    # Skip Saturday (5) and Sunday (6).
    while time.weekday() >= 5:
        time = time + timedelta(days=1)

    return time


def make_forecast_path(symbol, bars, forecast, session_open, session_close):
    """The forecast as a list of prices, one per trading minute, from the last
    real bar to the target price. The chart draws these as orange candles.

    A straight line would look unnatural, so we add random ups and downs the
    same size as the stock's usual minute-to-minute moves. The line is then
    bent so it still ends exactly on the target price. The wiggles only show
    what a typical path looks like; the forecast itself is the end point.
    """
    if len(bars) < 2:
        return []

    start_price = bars[-1]["close"]
    target_price = forecast["target_price"]

    # How much the price usually moves in one minute, in percent
    # (the average size of the moves over the last 2 hours).
    recent = bars[-121:]
    moves = []
    for i in range(1, len(recent)):
        moves.append(abs(recent[i]["close"] / recent[i - 1]["close"] - 1) * 100)
    typical_move = sum(moves) / len(moves)

    # A random walk: each minute, a random step up or down of about that size.
    # Using the stock and date as the "seed" gives the same random shape every
    # time the page refreshes, instead of a new jumpy shape every 5 seconds.
    rng = random.Random(symbol + bars[-1]["time"][:10])
    walk = [0]
    for minute in range(FORECAST_MINUTES):
        walk.append(walk[-1] + rng.gauss(0, typical_move))

    path = []
    time = datetime.fromisoformat(bars[-1]["time"])
    for minute in range(FORECAST_MINUTES + 1):
        progress = minute / FORECAST_MINUTES
        straight_line = start_price + (target_price - start_price) * progress
        # Bend the walk so it's 0 at the start and 0 at the end,
        # which makes the path finish exactly on the target price.
        wiggle = walk[minute] - walk[-1] * progress
        path.append({
            "time": time.isoformat(),
            "price": straight_line * (1 + wiggle / 100),
        })
        time = next_trading_minute(time, session_open, session_close)

    return path
