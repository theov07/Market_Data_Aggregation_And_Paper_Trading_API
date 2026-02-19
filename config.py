"""
Configuration for the Market Data Aggregation system
"""
import os
import secrets

# Database
DB_PATH = "users.db"

# API Server
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
BASE_URL = f"http://localhost:{API_PORT}"

# Authentication
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

# Market type: "futures" or "spot"
MARKET_TYPE = "futures"

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

# Exchange WebSocket endpoints
BINANCE_WS_FUTURES = "wss://fstream.binance.com"
BINANCE_WS_SPOT = "wss://stream.binance.com:9443"
OKX_WS_BASE = "wss://ws.okx.com:8443/ws/v5/public"

# Get active Binance endpoint based on market type
BINANCE_WS_BASE = BINANCE_WS_FUTURES if MARKET_TYPE == "futures" else BINANCE_WS_SPOT
