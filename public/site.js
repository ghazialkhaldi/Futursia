// ---------------------------------------------------------------------------
// Page state
// ---------------------------------------------------------------------------

let stocks = {}; // symbol -> company name, loaded from the server
let currentSymbol = "AAPL";

const MINUTE = 60 * 1000;

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function setText(id, text, className) {
  const element = document.getElementById(id);
  element.textContent = text;
  if (className !== undefined) element.className = className;
}

function money(value) {
  if (value == null) return "-";
  return "$" + value.toFixed(2);
}

// Adds a + in front of positive numbers, e.g. +1.25%
function signed(value, digits, suffix = "") {
  if (value == null) return "-";
  const sign = value >= 0 ? "+" : "";
  return sign + value.toFixed(digits) + suffix;
}

// Green for up, red for down, grey for flat.
function colorFor(value) {
  if (value > 0 || value === "UP") return "txt-up";
  if (value < 0 || value === "DOWN") return "txt-down";
  return "txt-flat";
}

function easternTime(date) {
  return new Date(date).toLocaleTimeString("en-US", { timeZone: "America/New_York" }) + " ET";
}

async function getJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error("Request failed: " + response.status);
  return response.json();
}

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  for (const tab of tabs) {
    tab.addEventListener("click", () => {
      for (const other of tabs) {
        const isThisOne = other === tab;
        other.classList.toggle("is-active", isThisOne);
        document.getElementById(other.dataset.panel).classList.toggle("is-active", isThisOne);
      }
      // The chart can't measure its size while hidden, so redraw it when shown.
      drawChart();
    });
  }
}

// ---------------------------------------------------------------------------
// Dashboard: top movers table
// ---------------------------------------------------------------------------

async function loadMovers() {
  try {
    const movers = await getJson("/api/movers");
    const tbody = document.getElementById("moversBody");
    tbody.innerHTML = "";

    for (const stock of movers) {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${stock.name}</td>
        <td>${money(stock.price)}</td>
        <td>${signed(stock.change, 2)}</td>
        <td class="${colorFor(stock.change_percent)}">${signed(stock.change_percent, 2, "%")}</td>
        <td>${money(stock.high)}</td>
        <td>${money(stock.low)}</td>
      `;
      tbody.appendChild(row);
    }
    setText("dashboardUpdated", "Updated " + easternTime(new Date()));
  } catch (error) {
    setText("dashboardUpdated", "Couldn't load data");
  }
}

// ---------------------------------------------------------------------------
// Ticker: search box and dropdown
// ---------------------------------------------------------------------------

// Symbols whose ticker or company name contains the search text.
function searchStocks(text) {
  const search = text.trim().toLowerCase();
  return Object.keys(stocks).filter((symbol) => {
    return symbol.toLowerCase().includes(search) || stocks[symbol].toLowerCase().includes(search);
  });
}

function fillDropdown(symbols) {
  const select = document.getElementById("tickerSelect");
  select.innerHTML = "";
  for (const symbol of symbols) {
    const option = document.createElement("option");
    option.value = symbol;
    option.textContent = `${stocks[symbol]} (${symbol})`;
    select.appendChild(option);
  }
  select.value = currentSymbol;
}

function selectStock(symbol) {
  if (!symbol || symbol === currentSymbol) return;
  currentSymbol = symbol;
  document.getElementById("tickerSelect").value = symbol;
  setText("tickerUpdated", "Loading...");
  resetChartView();
  loadTicker();
}

function setupSearch() {
  const search = document.getElementById("tickerSearch");
  const select = document.getElementById("tickerSelect");

  search.addEventListener("input", () => {
    fillDropdown(searchStocks(search.value));
  });

  // Press Enter to jump to the first match.
  search.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      const matches = searchStocks(search.value);
      selectStock(matches[0]);
    }
  });

  select.addEventListener("change", () => selectStock(select.value));
}

// ---------------------------------------------------------------------------
// Ticker: price, forecast and market cards
// ---------------------------------------------------------------------------

async function loadTicker() {
  const symbol = currentSymbol;
  try {
    const data = await getJson("/api/ticker/" + encodeURIComponent(symbol));
    // If the user picked another stock while we were waiting, ignore this answer.
    if (symbol !== currentSymbol) return;
    showTicker(data);
  } catch (error) {
    setText("tickerUpdated", "Couldn't load data");
  }
}

function showTicker(data) {
  const { quote, forecast } = data;

  setText("tickerName", `${data.name} (${data.symbol})`);
  setText("tickerUpdated", "Updated " + easternTime(new Date()));
  document.title = `${data.symbol} | Futursia`;

  setText("priceValue", money(quote.price));
  setText("priceChange", signed(quote.change_percent, 2, "% today"), colorFor(quote.change_percent));

  setText("forecastDirection", forecast.direction, colorFor(forecast.direction));
  setText(
    "forecastReturn",
    signed(forecast.return_percent, 3, "%") + " → " + money(forecast.target_price),
    colorFor(forecast.direction)
  );

  // e.g. "0.83% below" when the price is under today's average.
  const difference = forecast.difference_percent;
  const aboveOrBelow = difference < 0 ? "below" : "above";
  setText("averageDifference", Math.abs(difference).toFixed(2) + "% " + aboveOrBelow);
  setText("averagePrice", "Today's average " + money(forecast.average_price));

  setText("marketStatus", data.market_open ? "OPEN" : "CLOSED", data.market_open ? "txt-up" : "txt-down");
  const lastBar = data.bars[data.bars.length - 1];
  setText("lastTrade", lastBar ? "Last trade " + easternTime(lastBar.time) : "-");

  setChartData(data.bars, data.forecast_path);
}

// ---------------------------------------------------------------------------
// Chart
// ---------------------------------------------------------------------------
//
// Green/red candles are real prices, orange candles are the forecast.
// viewStart / viewEnd are the times (in ms) at the left and right edges.

let liveCandles = [];
let forecastCandles = [];
let viewStart = null;
let viewEnd = null;

function setChartData(bars, forecastPath) {
  liveCandles = bars.map((bar) => ({
    time: new Date(bar.time).getTime(),
    open: bar.open,
    high: bar.high,
    low: bar.low,
    close: bar.close,
  }));

  // Turn each step of the forecast line into a candle.
  forecastCandles = [];
  for (let i = 1; i < forecastPath.length; i++) {
    const open = forecastPath[i - 1].price;
    const close = forecastPath[i].price;
    forecastCandles.push({
      time: new Date(forecastPath[i].time).getTime(),
      open,
      close,
      high: Math.max(open, close),
      low: Math.min(open, close),
    });
  }

  if (viewStart === null) resetChartView();
  drawChart();
}

function allCandles() {
  return liveCandles.concat(forecastCandles);
}

// Show the last 3 hours of prices plus the 3-hour forecast.
function resetChartView() {
  const candles = allCandles();
  if (candles.length === 0) {
    viewStart = null;
    viewEnd = null;
    return;
  }
  viewEnd = candles[candles.length - 1].time + 2 * MINUTE;
  viewStart = Math.max(candles[0].time, viewEnd - 6 * 60 * MINUTE);
}

// Stop the user from zooming or dragging too far away from the data.
function keepViewInRange() {
  const candles = allCandles();
  const first = candles[0].time - 5 * MINUTE;
  const last = candles[candles.length - 1].time + 5 * MINUTE;

  let width = viewEnd - viewStart;
  width = Math.max(width, 10 * MINUTE); // at least 10 minutes
  width = Math.min(width, last - first); // at most all the data

  let start = viewStart;
  start = Math.max(start, first);
  start = Math.min(start, last - width);

  viewStart = start;
  viewEnd = start + width;
}

// factor < 1 zooms in, > 1 zooms out. anchor (0 to 1) is the point that stays still.
function zoom(factor, anchor = 0.5) {
  if (viewStart === null) return;
  const anchorTime = viewStart + (viewEnd - viewStart) * anchor;
  viewStart = anchorTime - (anchorTime - viewStart) * factor;
  viewEnd = anchorTime + (viewEnd - anchorTime) * factor;
  drawChart();
}

function svgElement(name, attributes) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const key in attributes) {
    element.setAttribute(key, attributes[key]);
  }
  return element;
}

function drawChart() {
  const svg = document.getElementById("priceChart");
  const width = svg.clientWidth;
  const height = svg.clientHeight;
  if (width === 0) return; // hidden tab
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = "";

  if (viewStart === null) {
    const message = svgElement("text", { x: width / 2, y: height / 2, fill: "#7f9199", "text-anchor": "middle" });
    message.textContent = "No chart data yet";
    svg.appendChild(message);
    return;
  }
  keepViewInRange();

  // Space around the plot for the axis labels.
  const left = 56;
  const right = width - 12;
  const top = 10;
  const bottom = height - 36;

  // Only the candles inside the current view.
  const visibleLive = liveCandles.filter((c) => c.time >= viewStart && c.time <= viewEnd);
  const visibleForecast = forecastCandles.filter((c) => c.time >= viewStart && c.time <= viewEnd);
  const visible = visibleLive.concat(visibleForecast);
  if (visible.length === 0) return;

  // Price range, with a little space above and below.
  let lowPrice = Math.min(...visible.map((c) => c.low));
  let highPrice = Math.max(...visible.map((c) => c.high));
  const padding = Math.max((highPrice - lowPrice) * 0.08, lowPrice * 0.002);
  lowPrice -= padding;
  highPrice += padding;

  // Convert a time to an x position and a price to a y position.
  const x = (time) => left + ((time - viewStart) / (viewEnd - viewStart)) * (right - left);
  const y = (price) => top + ((highPrice - price) / (highPrice - lowPrice)) * (bottom - top);

  // Horizontal grid lines with prices.
  for (let i = 0; i <= 5; i++) {
    const lineY = top + ((bottom - top) * i) / 5;
    svg.appendChild(svgElement("line", { x1: left, x2: right, y1: lineY, y2: lineY, stroke: "#253037" }));
    const label = svgElement("text", { x: 8, y: lineY + 4, fill: "#90a4ad", "font-size": 10 });
    label.textContent = (highPrice - ((highPrice - lowPrice) * i) / 5).toFixed(2);
    svg.appendChild(label);
  }

  // Vertical grid lines with times.
  for (let i = 0; i <= 6; i++) {
    const lineX = left + ((right - left) * i) / 6;
    svg.appendChild(svgElement("line", { x1: lineX, x2: lineX, y1: top, y2: bottom, stroke: "#1d272d" }));
    const label = svgElement("text", { x: lineX, y: height - 8, fill: "#89a0a9", "font-size": 10, "text-anchor": "middle" });
    const time = viewStart + ((viewEnd - viewStart) * i) / 6;
    label.textContent = new Date(time).toLocaleString("en-US", {
      month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
    });
    svg.appendChild(label);
  }

  // Each candle is a thin line (high to low) plus a box (open to close).
  const candleWidth = Math.max(1, Math.min(14, (MINUTE / (viewEnd - viewStart)) * (right - left) * 0.7));

  function drawCandle(candle, color) {
    const centerX = x(candle.time);
    const boxTop = Math.min(y(candle.open), y(candle.close));
    const boxHeight = Math.max(1, Math.abs(y(candle.open) - y(candle.close)));
    svg.appendChild(svgElement("line", { x1: centerX, x2: centerX, y1: y(candle.high), y2: y(candle.low), stroke: color }));
    svg.appendChild(svgElement("rect", { x: centerX - candleWidth / 2, y: boxTop, width: candleWidth, height: boxHeight, fill: color }));
  }

  for (const candle of visibleLive) {
    drawCandle(candle, candle.close >= candle.open ? "#25c26e" : "#ef5350");
  }
  for (const candle of visibleForecast) {
    drawCandle(candle, "#ff9f43");
  }
}

function setupChartControls() {
  const svg = document.getElementById("priceChart");

  document.getElementById("zoomInButton").addEventListener("click", () => zoom(0.85));
  document.getElementById("zoomOutButton").addEventListener("click", () => zoom(1.15));
  document.getElementById("resetButton").addEventListener("click", () => {
    resetChartView();
    drawChart();
  });
  svg.addEventListener("dblclick", () => {
    resetChartView();
    drawChart();
  });

  // Mouse wheel zooms around the mouse position.
  svg.addEventListener("wheel", (event) => {
    event.preventDefault();
    const box = svg.getBoundingClientRect();
    const anchor = (event.clientX - box.left) / box.width;
    zoom(event.deltaY < 0 ? 0.85 : 1.15, anchor);
  }, { passive: false });

  // Click and drag to move left and right.
  let dragStartX = null;
  let dragStartView = null;

  svg.addEventListener("pointerdown", (event) => {
    if (viewStart === null) return;
    dragStartX = event.clientX;
    dragStartView = viewStart;
    svg.setPointerCapture(event.pointerId);
  });

  svg.addEventListener("pointermove", (event) => {
    if (dragStartX === null) return;
    const width = viewEnd - viewStart;
    const movedTime = ((event.clientX - dragStartX) / svg.clientWidth) * width;
    viewStart = dragStartView - movedTime;
    viewEnd = viewStart + width;
    drawChart();
  });

  svg.addEventListener("pointerup", () => (dragStartX = null));
  svg.addEventListener("pointercancel", () => (dragStartX = null));

  window.addEventListener("resize", drawChart);
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

async function start() {
  setupTabs();
  setupSearch();
  setupChartControls();

  stocks = await getJson("/api/stocks");
  fillDropdown(Object.keys(stocks));

  loadMovers();
  loadTicker();

  // Keep the data fresh. The server only asks Yahoo for new data every
  // 5 seconds (ticker) and 30 seconds (movers), so polling faster wouldn't help.
  setInterval(loadMovers, 30 * 1000);
  setInterval(loadTicker, 5 * 1000);
}

start();
