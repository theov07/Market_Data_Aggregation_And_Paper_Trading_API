"""
Normalise raw WebSocket messages into typed Python structures
and maintain in-memory snapshots of the latest market data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BestTouchSnapshot:
    symbol:         str
    exchange:       str       # always "all" for aggregated best-touch
    best_bid_price: float
    best_ask_price: float
    bid_exchange:   str = "?"
    ask_exchange:   str = "?"
    timestamp:      Optional[str] = None

    @property
    def spread(self) -> float:
        return self.best_ask_price - self.best_bid_price

    @property
    def mid(self) -> float:
        return (self.best_bid_price + self.best_ask_price) / 2


@dataclass
class TradeSnapshot:
    symbol:    str
    exchange:  str
    price:     float
    quantity:  float
    side:      str
    timestamp: Optional[str] = None
    trade_id:  Optional[str] = None


@dataclass
class KlineSnapshot:
    symbol:    str
    exchange:  str
    interval:  str
    open:      float
    high:      float
    low:       float
    close:     float
    volume:    float
    open_time: Optional[str] = None
    close_time: Optional[str] = None


@dataclass
class EWMASnapshot:
    symbol:    str
    exchange:  str
    half_life: float
    value:     float
    timestamp: Optional[str] = None


@dataclass
class MarketDataStore:
    """In-memory store updated by calling process_message()."""
    best_touch: dict[str, dict[str, BestTouchSnapshot]] = field(default_factory=dict)
    # symbol -> exchange -> snapshot list (last 200)
    trades: dict[str, list[TradeSnapshot]] = field(default_factory=dict)
    # symbol -> exchange -> interval -> snapshot list (last 200)
    klines: dict[str, dict[str, dict[str, list[KlineSnapshot]]]] = field(default_factory=dict)
    # symbol -> exchange -> half_life -> snapshot
    ewma: dict[str, dict[str, dict[str, EWMASnapshot]]] = field(default_factory=dict)
    # all raw messages (last 500)
    log: list[dict] = field(default_factory=list)

    def process_message(self, msg: dict):
        """Update store with one WS message."""
        self.log.append(msg)
        if len(self.log) > 500:
            self.log = self.log[-500:]

        t = msg.get("type")
        data = msg.get("data", {})

        if t == "best_touch":
            self._update_best_touch(data)
        elif t == "trade":
            self._update_trade(data)
        elif t == "kline":
            self._update_kline(data)
        elif t == "ewma":
            self._update_ewma(data)

    def _update_best_touch(self, data: dict):
        sym = data.get("symbol", "?")
        # exchange field is "all" for cross-exchange aggregation, or a specific exchange name
        exc = data.get("exchange", "all")
        snap = BestTouchSnapshot(
            symbol=sym,
            exchange=exc,
            best_bid_price=float(data.get("bid_price", 0)),
            best_ask_price=float(data.get("ask_price", 0)),
            bid_exchange=data.get("bid_exchange", "?"),
            ask_exchange=data.get("ask_exchange", "?"),
            timestamp=data.get("timestamp"),
        )
        self.best_touch.setdefault(sym, {})[exc] = snap

    def _update_trade(self, data: dict):
        sym = data.get("symbol", "?")
        exc = data.get("exchange", "?")
        snap = TradeSnapshot(
            symbol=sym,
            exchange=exc,
            price=float(data.get("price", 0)),
            quantity=float(data.get("quantity", 0)),
            side=data.get("side", "?"),
            timestamp=data.get("timestamp"),
            trade_id=str(data.get("trade_id", "")),
        )
        bucket = self.trades.setdefault(sym, [])
        bucket.append(snap)
        if len(bucket) > 200:
            self.trades[sym] = bucket[-200:]

    def _update_kline(self, data: dict):
        sym = data.get("symbol", "?")
        exc = data.get("exchange", "?")
        ivl = data.get("interval", "?")
        snap = KlineSnapshot(
            symbol=sym,
            exchange=exc,
            interval=ivl,
            open=float(data.get("open", 0)),
            high=float(data.get("high", 0)),
            low=float(data.get("low", 0)),
            close=float(data.get("close", 0)),
            volume=float(data.get("volume", 0)),
            open_time=data.get("open_time"),
            close_time=data.get("close_time"),
        )
        sym_d = self.klines.setdefault(sym, {})
        exc_d = sym_d.setdefault(exc, {})
        bucket = exc_d.setdefault(ivl, [])
        bucket.append(snap)
        if len(bucket) > 200:
            exc_d[ivl] = bucket[-200:]

    def _update_ewma(self, data: dict):
        sym = data.get("symbol", "?")
        exc = data.get("exchange", "?")
        hl = str(data.get("half_life", "?"))
        snap = EWMASnapshot(
            symbol=sym,
            exchange=exc,
            half_life=float(data.get("half_life", 0)),
            value=float(data.get("value", 0)),
            timestamp=data.get("timestamp"),
        )
        self.ewma.setdefault(sym, {}).setdefault(exc, {})[hl] = snap
