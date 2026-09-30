# The 3-hour forecast.
#
# Idea: over the next 3 hours, a stock tends to drift back toward its
# average price for the day. If it's trading above today's average we lean
# DOWN, if below we lean UP.
#
# We tested this on 60 days of 5-minute data for all 90 stocks on the site.
# Over 3 hours it picked the right direction about 52-54% of the time, which
# is better than over 40 minutes (51%). When the price is very close to the
# average the result was a coin flip, so we say FLAT.
#
# We also tested days, weeks and months ahead. Over those, the only thing
# that could be predicted was that stocks in general tend to rise, so every
# stock would just say UP. 3 hours was the best time span for this rule.

from datetime import datetime, timedelta

FORECAST_MINUTES = 3 * 60  # 3 hours


def make_forecast(bars):
    if len(bars) == 0:
        return {"direction": "FLAT", "return_percent": 0, "confidence": 50, "target_price": None}

    # Only use bars from the most recent trading day.
    # The first 10 characters of the time are the date, like "2026-09-30".
    last_day = bars[-1]["time"][:10]
    today_bars = [bar for bar in bars if bar["time"][:10] == last_day]

    price = today_bars[-1]["close"]
    total = 0
    for bar in today_bars:
        total += bar["close"]
    average = total / len(today_bars)

    # How far the average is from the price, in percent.
    # Positive = price is below the average (expect a move up).
    gap_percent = (average - price) / price * 100
    gap_size = abs(gap_percent)

    # Expect the price to close about 8% of that gap in 3 hours.
    # (0.08 is the best fit from the test data.)
    return_percent = gap_percent * 0.08

    # Confidence = how often the direction was right in testing.
    direction = "FLAT"
    confidence = 50
    if gap_size >= 0.1:
        direction = "UP" if gap_percent > 0 else "DOWN"
        confidence = 54 if gap_size >= 0.25 else 52

    return {
        "direction": direction,
        "return_percent": return_percent,
        "confidence": confidence,
        "target_price": price * (1 + return_percent / 100),
    }


def make_forecast_path(bars, forecast):
    """The forecast as a straight line of prices, one per minute, from the
    last real bar to the target price. The chart draws these as orange candles."""
    if len(bars) == 0:
        return []

    last_bar = bars[-1]
    start_time = datetime.fromisoformat(last_bar["time"])
    start_price = last_bar["close"]
    path = []

    for minute in range(FORECAST_MINUTES + 1):
        progress = minute / FORECAST_MINUTES
        path.append({
            "time": (start_time + timedelta(minutes=minute)).isoformat(),
            "price": start_price + (forecast["target_price"] - start_price) * progress,
        })

    return path
