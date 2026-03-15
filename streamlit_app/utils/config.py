"""
Streamlit app configuration — mirrors backend constants.
"""

API_BASE = "http://localhost:8000"
WS_BASE  = "ws://localhost:8000/ws"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT"]

EXCHANGES = ["binance", "okx", "all"]

KLINE_INTERVALS = ["1s", "10s", "1m", "5m"]

DATA_TYPES = ["best_touch", "trade", "kline", "ewma"]

SIDES = ["buy", "sell"]

ORDER_TYPES = ["limit", "market", "ioc"]

STATUS_COLORS = {
    "open":      "#3b82f6",   # blue
    "filled":    "#22c55e",   # green
    "cancelled": "#f97316",   # orange
    "rejected":  "#ef4444",   # red
}

SIDE_COLORS = {
    "buy":  "#22c55e",
    "sell": "#ef4444",
}

# Refresh interval used by live pages (seconds)
LIVE_REFRESH_INTERVAL = 2
