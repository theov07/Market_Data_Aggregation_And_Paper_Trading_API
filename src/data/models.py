"""
Data models for market data
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class OrderBookLevel:
    """Represents a single level in the order book"""
    price: float
    quantity: float
    exchange: Literal["binance", "okx"]


@dataclass
class BestTouch:
    """Best bid and ask across exchanges"""
    symbol: str
    best_bid_price: float
    best_bid_quantity: float
    best_bid_exchange: str
    best_ask_price: float
    best_ask_quantity: float
    best_ask_exchange: str
    timestamp: datetime


@dataclass
class Trade:
    """Represents a single trade"""
    symbol: str
    price: float
    quantity: float
    side: Literal["buy", "sell"]
    timestamp: datetime
    exchange: Literal["binance", "okx"]
    trade_id: str


@dataclass
class Kline:
    """Candlestick data"""
    symbol: str
    interval: str
    open_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    exchange: str
    is_closed: bool = False


@dataclass
class EWMA:
    """Exponential Weighted Moving Average"""
    symbol: str
    value: float
    half_life: float
    timestamp: datetime
    exchange: str
