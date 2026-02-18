"""
WebSocket documentation endpoint
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class WebSocketDocumentation(BaseModel):
    """WebSocket API documentation"""
    endpoint: str = Field(description="WebSocket endpoint URL")
    protocol: str = Field(description="WebSocket protocol")
    description: str = Field(description="Endpoint description")
    
    class SubscriptionFormat(BaseModel):
        action: str = Field(description="subscribe or unsubscribe")
        data_type: str = Field(description="Type of data: best_touch, trade, kline, ewma")
        symbol: str = Field(description="Trading pair symbol (e.g., BTCUSDT)")
        exchange: str = Field(default="all", description="all, binance, or okx")
        interval: str | None = Field(default=None, description="Required for kline subscriptions (e.g., 1m, 5m)")
    
    subscription_format: SubscriptionFormat = Field(description="Format for subscription messages")
    
    class DataExamples(BaseModel):
        best_touch_example: dict = Field(description="Example of best_touch data")
        trade_example: dict = Field(description="Example of trade data")
        kline_example: dict = Field(description="Example of kline data")
        ewma_example: dict = Field(description="Example of EWMA data")
    
    data_examples: DataExamples = Field(description="Examples of data messages")


@router.get(
    "/ws-docs",
    response_model=WebSocketDocumentation,
    summary="WebSocket API Documentation",
    description="""
    Get detailed documentation about the WebSocket API.
    
    The WebSocket endpoint at `/ws` allows real-time streaming of market data.
    
    **How to connect:**
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws');
    ```
    
    **Subscribe to data:**
    ```json
    {
        "action": "subscribe",
        "data_type": "best_touch",
        "symbol": "BTCUSDT",
        "exchange": "all"
    }
    ```
    
    **Data types:**
    - `best_touch`: Best bid/ask across exchanges (cross-exchange arbitrage detection)
    - `trade`: Individual trades from exchanges
    - `kline`: OHLCV candlesticks (requires interval: 1s, 10s, 1m, 5m)
    - `ewma`: Exponential Weighted Moving Average
    
    **Exchange filters:**
    - `all`: Data from all exchanges
    - `binance`: Only Binance data
    - `okx`: Only OKX data
    """,
    tags=["WebSocket"],
    responses={
        200: {
            "description": "WebSocket documentation",
            "content": {
                "application/json": {
                    "example": {
                        "endpoint": "/ws",
                        "protocol": "WebSocket",
                        "description": "Real-time market data streaming",
                        "subscription_format": {
                            "action": "subscribe",
                            "data_type": "best_touch",
                            "symbol": "BTCUSDT",
                            "exchange": "all",
                            "interval": "1m"
                        },
                        "data_examples": {
                            "best_touch_example": {
                                "type": "best_touch",
                                "data": {
                                    "symbol": "BTCUSDT",
                                    "bid_price": 68090.0,
                                    "bid_exchange": "binance",
                                    "ask_price": 68087.6,
                                    "ask_exchange": "okx",
                                    "spread": -2.4,
                                    "timestamp": 1708272000.123
                                },
                                "timestamp": 1708272000.123
                            },
                            "trade_example": {
                                "type": "trade",
                                "data": {
                                    "symbol": "ETHUSDT",
                                    "exchange": "binance",
                                    "price": 2014.67,
                                    "quantity": 0.5,
                                    "timestamp": 1708272000.123
                                },
                                "timestamp": 1708272000.123
                            },
                            "kline_example": {
                                "type": "kline",
                                "data": {
                                    "symbol": "SOLUSDT",
                                    "exchange": "binance",
                                    "interval": "1m",
                                    "open": 100.5,
                                    "high": 101.2,
                                    "low": 100.3,
                                    "close": 100.8,
                                    "volume": 1234.56,
                                    "open_time": 1708272000.0,
                                    "close_time": 1708272060.0
                                },
                                "timestamp": 1708272060.123
                            },
                            "ewma_example": {
                                "type": "ewma",
                                "data": {
                                    "symbol": "BNBUSDT",
                                    "exchange": "okx",
                                    "value": 305.67,
                                    "timestamp": 1708272000.123
                                },
                                "timestamp": 1708272000.123
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_websocket_docs() -> dict:
    """Get WebSocket API documentation"""
    return {
        "endpoint": "/ws",
        "protocol": "WebSocket",
        "description": "Real-time market data streaming with subscription-based filtering",
        "subscription_format": {
            "action": "subscribe or unsubscribe",
            "data_type": "best_touch | trade | kline | ewma",
            "symbol": "Trading pair (e.g., BTCUSDT)",
            "exchange": "all | binance | okx (default: all)",
            "interval": "Required for kline: 1s | 10s | 1m | 5m"
        },
        "data_examples": {
            "best_touch_example": {
                "type": "best_touch",
                "data": {
                    "symbol": "BTCUSDT",
                    "bid_price": 68090.0,
                    "bid_exchange": "binance",
                    "ask_price": 68087.6,
                    "ask_exchange": "okx",
                    "spread": -2.4,
                    "timestamp": 1708272000.123
                },
                "timestamp": 1708272000.123
            },
            "trade_example": {
                "type": "trade",
                "data": {
                    "symbol": "ETHUSDT",
                    "exchange": "binance",
                    "price": 2014.67,
                    "quantity": 0.5,
                    "timestamp": 1708272000.123
                },
                "timestamp": 1708272000.123
            },
            "kline_example": {
                "type": "kline",
                "data": {
                    "symbol": "SOLUSDT",
                    "exchange": "binance",
                    "interval": "1m",
                    "open": 100.5,
                    "high": 101.2,
                    "low": 100.3,
                    "close": 100.8,
                    "volume": 1234.56,
                    "open_time": 1708272000.0,
                    "close_time": 1708272060.0
                },
                "timestamp": 1708272060.123
            },
            "ewma_example": {
                "type": "ewma",
                "data": {
                    "symbol": "BNBUSDT",
                    "exchange": "okx",
                    "value": 305.67,
                    "timestamp": 1708272000.123
                },
                "timestamp": 1708272000.123
            }
        }
    }
