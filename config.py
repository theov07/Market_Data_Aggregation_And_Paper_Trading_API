"""
Configuration for the Market Data Aggregation system
"""

# Trading pairs to monitor
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "ADAUSDT"
]

# Kline intervals in seconds
KLINE_INTERVALS = {
    "1s": 1,
    "10s": 10,
    "1m": 60,
    "5m": 300
}

# Exchange endpoints
BINANCE_WS_BASE = "wss://stream.binance.com:9443/ws"
OKX_WS_BASE = "wss://ws.okx.com:8443/ws/v5/public"
