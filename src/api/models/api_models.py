"""
API models for FastAPI endpoints
"""
from typing import Literal
from pydantic import BaseModel, Field


class InfoResponse(BaseModel):
    """Response for GET /info endpoint"""
    assets: list[str]
    trading_pairs: list[str]
    exchanges: list[str]
    kline_intervals: list[str]


class WebSocketSubscription(BaseModel):
    """WebSocket subscription message from client"""
    action: Literal["subscribe", "unsubscribe"]
    data_type: Literal["best_touch", "trade", "kline", "ewma"]
    symbol: str
    exchange: Literal["all", "binance", "okx"] = "all"
    interval: str | None = Field(None, description="Required for kline subscriptions")


class WebSocketMessage(BaseModel):
    """Generic WebSocket message sent to client"""
    type: str
    data: dict
    timestamp: float
