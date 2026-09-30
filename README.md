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
the day. If it's above today's average the forecast is DOWN, below it's UP. The
expected move is 8% of the gap between the price and the average. If the price
is within 0.1% of the average, the forecast is FLAT.

Tested on 60 days of 5-minute data for all 90 stocks, it picked the right
direction 52% of the time, and about 54% when the price was 0.25% or more
away from its average. That's better than a 40-minute forecast (51%).

Longer forecasts (days to months) were also tested. Over those, the only
pattern was that stocks in general tend to go up, so every stock would just
say UP. Short-term moves are mostly random, so treat the forecast as a small
lean, not something you can count on.
