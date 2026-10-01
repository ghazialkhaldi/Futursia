# Futursia

A stock dashboard with a 3-hour price forecast for 90 US and Canadian stocks.

## Run it

You need Python 3.9 or newer.

```
pip install -r requirements.txt
python app.py
```

Then open http://localhost:8000

## Files

- `app.py` - the web server. Sends the page and answers the page's data requests.
- `yahoo.py` - downloads prices from Yahoo Finance.
- `forecast.py` - makes the 3-hour forecast.
- `stocks.py` - the list of stocks. Add a line here to add a stock.
- `public/index.html` - the page layout.
- `public/site.js` - loads data from the server and draws the table and chart.
- `public/site.css` - colors and layout.
- `api/index.py`, `vercel.json` and `requirements.txt` - let Vercel run the same server.

## How the forecast works

Over the next 3 hours a stock tends to drift back toward its average price for
the day. If it's below today's average the forecast is UP, above it's DOWN. The
expected move is 8% of the way back to the average. If the price is within
0.1% of the average, the forecast is FLAT. The Ticker page shows how far the
price is from today's average, so you can see how strong the signal is.

How well it works: on 60 days of 5-minute data for all 90 stocks it picked the
right direction 52-54% of the time, but on 2 years of hourly data only 50.6%.
So it's only a little better than a coin flip, and treat it as a small lean,
not something you can count on.

Longer forecasts (days to months) were also tested. Over those, the only
pattern was that stocks in general tend to go up, so every stock would just
say UP.
