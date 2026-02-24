"""
API models for FastAPI endpoints
"""
from typing import Literal
from pydantic import BaseModel, Field


class InfoResponse(BaseModel):
    """
    Response for GET /info endpoint
    """
    assets: list[str]
    trading_pairs: list[str]
    exchanges: list[str]
    kline_intervals: list[str]


class WebSocketSubscription(BaseModel):
    """
    WebSocket subscription message from client
    """
    action: Literal["subscribe", "unsubscribe"]
    data_type: Literal["best_touch", "trade", "kline", "ewma"]
    symbol: str
    exchange: Literal["all", "binance", "okx"] = "all"
    interval: str | None = Field(None, description="Required for kline subscriptions")
    half_life: float | None = Field(
        None, 
        gt=0, 
        le=3600, 
        description="EWMA half-life in seconds (1-3600). Default: 30. Only used for ewma subscriptions."
    )


class WebSocketOrderSubmit(BaseModel):
    """
    WebSocket order submission message
    """
    action: Literal["submit_order"]
    token_id: str
    symbol: str
    side: Literal["buy", "sell"]
    price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)


class WebSocketOrderCancel(BaseModel):
    """
    WebSocket order cancellation message
    """
    action: Literal["cancel_order"]
    token_id: str


class WebSocketOrderUpdate(BaseModel):
    """
    WebSocket order update message sent to client
    """
    type: Literal["order_update"]
    order_id: int
    token_id: str
    symbol: str
    side: str
    price: float
    quantity: float
    status: str
    created_at: str
    executed_at: str | None = None


class WebSocketMessage(BaseModel):
    """
    Generic WebSocket message sent to client
    """
    type: str
    data: dict
    timestamp: float
