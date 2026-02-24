# Market Data Aggregation & Paper Trading API

**Real-time cryptocurrency data router and paper trading engine with cross-exchange aggregation and WebSocket streaming.**

*Academic project - Paris Dauphine University - Master 2 in Financial Engineering - Major in Quantitative Finance*

---

## Overview

Multi-exchange market data aggregator that maintains persistent WebSocket connections to Binance and OKX, providing unified real-time data streams to clients. The system includes a paper trading engine for simulated order execution against live order books.

**Key Features:**
- Real-time order book and trade aggregation from Binance Futures and OKX Perpetual Swaps
- WebSocket API for streaming market data (best touch, trades, klines, EWMA)
- JWT-based authentication with secure password storage
- Paper trading engine with fund management and order execution
- Cross-exchange arbitrage opportunity detection
- Persistent storage with SQLite database

---

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd Market_Data_Aggregation_And_Paper_Trading_API

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Launch Server

```bash
python run_server.py
```

Server starts at `http://localhost:8000`

**API Documentation:** `http://localhost:8000/docs` (Swagger UI)

### Run Demo Client

Execute the interactive notebook:
```bash
jupyter notebook client_demo.ipynb
```


The demo demonstrates all API features: authentication, market data subscriptions, fund deposits, order management, and WebSocket streaming.

---

## Features

### Market Data Aggregation

**Supported Exchanges:**
- Binance Futures (`wss://fstream.binance.com`)
- OKX Perpetual Swaps (`wss://ws.okx.com:8443/ws/v5/public`)

**Trading Pairs:**
- BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT, ADA/USDT

**Data Streams:**
- **Best Touch**: Best bid/ask price and volume across exchanges with arbitrage detection
- **Trades**: Real-time trade feed with exchange routing
- **Klines**: Live candlesticks (1s, 10s, 1m, 5m intervals) built from WebSocket data
- **EWMA**: Exponential weighted moving average with configurable half-life

All streams support exchange filtering: `all`, `binance`, or `okx`

### Authentication

- **Registration**: POST `/auth/register` with username/password
- **Login**: POST `/auth/login` returns JWT token
- **Security**: bcrypt password hashing, HS256 signed tokens
- **Validation**: Username format checking, duplicate prevention

### Paper Trading Engine

**Fund Management:**
- Deposit assets via POST `/deposit`
- View balances via GET `/balance` (total, available, reserved)
- Multi-asset support (BTC, ETH, SOL, BNB, ADA, USDT)

**Order Types:**
- **Limit Orders**: Execute when best touch crosses limit price
- **Market Orders**: Immediate execution at current best price
- **IOC (Immediate-Or-Cancel)**: Fill what's available, cancel remainder

**Order Management:**
- Submit: POST `/orders` with unique token_id
- Query: GET `/orders/{token_id}`
- Modify: PUT `/orders/{token_id}` (price and/or quantity)
- Cancel: DELETE `/orders/{token_id}` (releases reserved funds)

**Execution Logic:**
- Buy orders: execute when `best_ask ≤ limit_price`
- Sell orders: execute when `best_bid ≥ limit_price`
- Balance validation with proper fund reservation
- Real-time execution monitoring against live order books

### Advanced Features (Bonus)

**WebSocket Order Management:**
- Submit and cancel orders via WebSocket connection
- Real-time order execution notifications
- Authenticated WebSocket endpoint: `ws://localhost:8000/ws?token={jwt_token}`

**Server Persistence:**
- SQLite database (`users.db`) for accounts, balances, and orders
- Data survives server restarts
- Order history tracking

**Arbitrage Detection:**
- Identifies negative spreads (bid > ask across exchanges)
- Displays profit opportunity and recommended strategy
- Example: Buy BTC on OKX at $63,136.90, sell on Binance at $63,142.40 → $5.50 profit/BTC

---

## API Reference

### REST Endpoints

**Public:**
```
POST /auth/register - Create account
POST /auth/login    - Authenticate (returns JWT)
GET  /info          - List available assets and trading pairs
```

**Authenticated (requires `Authorization: Bearer {token}`):**
```
POST   /deposit              - Deposit funds
POST   /orders               - Submit order
GET    /orders/{token_id}    - Get order status
PUT    /orders/{token_id}    - Modify order
DELETE /orders/{token_id}    - Cancel order
GET    /balance              - Get account balances
```

### WebSocket API

**Connection:**
```
ws://localhost:8000/ws?token={jwt_token}
```

**Subscription Messages:**
```json
{
  "action": "subscribe",
  "data_type": "best_touch",
  "symbol": "BTCUSDT",
  "exchange": "all"
}

{
  "action": "subscribe",
  "data_type": "kline",
  "symbol": "ETHUSDT",
  "interval": "1m",
  "exchange": "binance"
}

{
  "action": "subscribe",
  "data_type": "ewma",
  "symbol": "SOLUSDT",
  "exchange": "all"
}
```

**Order Operations:**
```json
{
  "action": "submit_order",
  "token_id": "unique-id",
  "symbol": "BTCUSDT",
  "side": "buy",
  "order_type": "limit",
  "price": 50000,
  "quantity": 0.1
}

{
  "action": "cancel_order",
  "token_id": "order-id"
}
```

---

## Project Structure

```
Market_Data_Aggregation_And_Paper_Trading_API/
│
├── run_server.py              # Server entry point
├── client_demo.ipynb          # Interactive demo notebook
├── config.py                  # Configuration (symbols, exchanges, intervals)
├── requirements.txt           # Python dependencies
│
├── src/
│   ├── exchanges/             # Exchange WebSocket connectors
│   │   ├── binance_ws.py      # Binance Futures connector
│   │   └── okx_ws.py          # OKX Perpetual Swaps connector
│   │
│   ├── processors/            # Data processing
│   │   ├── kline_builder.py   # Live candlestick aggregation
│   │   └── ewma_calculator.py # Moving average computation
│   │
│   ├── api/
│   │   ├── server.py          # FastAPI application
│   │   ├── routes/            # API endpoints
│   │   │   ├── auth.py        # Authentication
│   │   │   ├── trading.py     # Orders and deposits
│   │   │   ├── websocket.py   # WebSocket subscriptions
│   │   │   └── info.py        # Asset/pair information
│   │   │
│   │   └── services/          
│   │       ├── auth_service.py           # User management
│   │       ├── trading_service.py        # Order processing
│   │       ├── market_data_service.py    # Data distribution
│   │       ├── order_execution_engine.py # Order matching
│   │       └── websocket_manager.py      # Client connections
│   │
│   └── data/
│       └── models.py          # Database models (SQLAlchemy)
│
└── users.db                   # SQLite database (auto-created)
└── view_users.py              # View database 
```

---

## Configuration

Edit `config.py` to customize:

**Market Type:**
```python
MARKET_TYPE = "futures"  # or "spot"
```

**Trading Pairs:**
```python
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    # Add more pairs...
]
```

**Kline Intervals:**
```python
KLINE_INTERVALS = {
    "1s": 1,
    "10s": 10,
    "1m": 60,
    "5m": 300
}
```

---

## Usage Examples

### Authentication

```python
import requests

BASE_URL = "http://localhost:8000"

# Register
response = requests.post(
    f"{BASE_URL}/auth/register",
    json={"username": "trader1", "password": "SecurePass123!"}
)
token = response.json()["access_token"]

# Use token for authenticated requests
headers = {"Authorization": f"Bearer {token}"}
```

### Market Data Subscription

```python
import asyncio
import websockets
import json

async def subscribe_best_touch():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        await ws.recv()  # Welcome message
        
        # Subscribe to best touch
        await ws.send(json.dumps({
            "action": "subscribe",
            "data_type": "best_touch",
            "symbol": "BTCUSDT",
            "exchange": "all"
        }))
        
        # Receive updates
        while True:
            message = await ws.recv()
            data = json.loads(message)
            print(f"Bid: ${data['data']['bid_price']:.2f}")
            print(f"Ask: ${data['data']['ask_price']:.2f}")
            print(f"Spread: ${data['data']['spread']:.2f}")

asyncio.run(subscribe_best_touch())
```

### Paper Trading

```python
# Deposit funds
response = requests.post(
    f"{BASE_URL}/deposit",
    json={"asset": "USDT", "amount": 10000},
    headers=headers
)

# Submit limit order
response = requests.post(
    f"{BASE_URL}/orders",
    json={
        "token_id": "order_123",
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "limit",
        "price": 50000.0,
        "quantity": 0.1
    },
    headers=headers
)

# Check order status
response = requests.get(
    f"{BASE_URL}/orders/order_123",
    headers=headers
)
print(response.json()["status"])  # "open", "filled", or "cancelled"

# Cancel order
response = requests.delete(
    f"{BASE_URL}/orders/order_123",
    headers=headers
)
```

---

## Technical Implementation

**Technology Stack:**
- **Framework**: FastAPI (async REST + WebSocket)
- **Database**: SQLite with aiosqlite (async operations)
- **Authentication**: JWT (python-jose), bcrypt password hashing
- **WebSocket Clients**: websockets library for exchange connections
- **Concurrency**: asyncio for concurrent client/exchange management

**Data Processing:**
- Klines built incrementally from trade data (no REST API usage)
- EWMA computed in real-time with decay factor: `α = 1 - exp(-ln(2) / half_life)`
- Order execution engine runs background task monitoring best touch every 100ms

**Performance:**
- Handles multiple concurrent client WebSocket connections
- Persistent exchange connections with automatic reconnection
- O(1) order lookup with in-memory indexing
- Database writes are asynchronous


---

## Dependencies

Install all:
```bash
pip install -r requirements.txt
```

---

## Project Requirements

**Mandatory Features:**
- Multi-exchange WebSocket connections (Binance + OKX)
- 5+ trading pairs configured
- Client WebSocket subscriptions (best touch, trades, klines, EWMA)
- Exchange filtering (all/binance/okx)
- JWT authentication with secure password storage
- Paper trading with balance management
- Limit order execution against live order books
- Order validation and error handling
- API documentation (Swagger auto-generated)

**Bonus Features (All Implemented):**
- WebSocket order management
- Server persistence (SQLite)
- Order modification (PUT endpoint)
- Additional order types (market, IOC)

---

**Authors:** VERDELHAN Théo, RENAULT Léo, AMIZET Cassandre, MARIANO Benjamin, BOUSSELMAME Adam  
**Institution:** Paris Dauphine University - Master 2 in Financial Engineering  
**Academic Year:** 2025/2026
