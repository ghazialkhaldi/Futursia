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
