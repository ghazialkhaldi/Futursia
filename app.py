# The web server. It sends the web page to the browser, and answers the
# page's requests for stock data.
#
# Run it on your computer with:  python app.py
# Then open http://localhost:8000

import os
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, jsonify, send_from_directory

from forecast import make_forecast, make_forecast_path
from stocks import STOCKS
from yahoo import get_bars, get_chart, get_quote, get_session_times, is_market_open

CHART_BARS = 240  # how many 1-minute bars to send to the chart (4 hours)
PUBLIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

# static_url_path="" means a file like public/site.js is available at /site.js
app = Flask(__name__, static_folder=PUBLIC_FOLDER, static_url_path="")
app.json.sort_keys = False  # keep the stocks in the order they're listed in stocks.py


@app.route("/")
def home():
    return send_from_directory(PUBLIC_FOLDER, "index.html")


@app.route("/api/stocks")
def stocks():
    """List of all stocks for the search box."""
    return jsonify(STOCKS)


def get_mover(symbol):
    """Today's price and change for one stock, or None if Yahoo fails."""
    try:
        chart = get_chart(symbol, "1d", "1d", 30)
        mover = get_quote(chart)
        mover["symbol"] = symbol
        mover["name"] = STOCKS[symbol]
        return mover
    except Exception:
        return None


@app.route("/api/movers")
def movers():
    """The 10 stocks that moved the most today (up or down)."""
    # Ask Yahoo about 20 stocks at a time instead of one after another,
    # otherwise 90 stocks would take several seconds.
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(get_mover, STOCKS.keys()))

    # Skip any stock that Yahoo failed to answer for.
    results = [mover for mover in results if mover is not None]

    # Biggest move first, whether it was up or down.
    results.sort(key=lambda mover: abs(mover["change_percent"]), reverse=True)
    return jsonify(results[:10])


@app.route("/api/ticker/<symbol>")
def ticker(symbol):
    """Everything the Ticker page needs for one stock."""
    symbol = symbol.upper()
    try:
        chart = get_chart(symbol, "5d", "1m", 5)
        bars = get_bars(chart)
        forecast = make_forecast(bars)
        session_open, session_close = get_session_times(chart)

        return jsonify({
            "symbol": symbol,
            "name": STOCKS.get(symbol, symbol),
            "quote": get_quote(chart),
            "market_open": is_market_open(chart),
            "forecast": forecast,
            "bars": bars[-CHART_BARS:],
            "forecast_path": make_forecast_path(symbol, bars, forecast, session_open, session_close),
        })
    except Exception as error:
        return jsonify({"error": str(error)}), 500


# This only runs when you start the file yourself (python app.py).
# On Vercel, api/index.py uses `app` directly instead.
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("Futursia running at http://localhost:" + str(port))
    app.run(port=port)
