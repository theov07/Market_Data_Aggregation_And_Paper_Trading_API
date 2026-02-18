"""
Market data service - coordinates exchange connections and data processing
"""
import asyncio
from typing import Dict

from config import SYMBOLS, KLINE_INTERVALS
from src.data.models import Trade, Kline, EWMA, BestTouch, OrderBookLevel
from src.exchanges.binance_ws import BinanceWebSocket
from src.exchanges.okx_ws import OKXWebSocket
from src.processors.kline_processor import KlineProcessor
from src.processors.ewma_processor import EWMAProcessor
from src.processors.best_touch import BestTouchAggregator
from src.utils.formatting import PriceFormatter
from .websocket_manager import WebSocketManager


class MarketDataService:
    """Main service for market data aggregation and broadcasting"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager
        self.price_formatter = PriceFormatter()
        self.best_touch_aggregator = BestTouchAggregator()
        
        # Create processors for each interval
        self.kline_processors: Dict[str, KlineProcessor] = {}
        self._init_kline_processors()
        
        # EWMA processor
        self.ewma_processor = EWMAProcessor(half_life_seconds=30)
        
        # Exchange clients
        self.binance_client: BinanceWebSocket | None = None
        self.okx_client: OKXWebSocket | None = None
        
        self._running = False
    
    def _init_kline_processors(self):
        """Initialize kline processors for each interval"""
        for interval_name, seconds in KLINE_INTERVALS.items():
            self.kline_processors[interval_name] = KlineProcessor(interval_seconds=seconds)
    
    async def start(self):
        """Start the market data service"""
        if self._running:
            return
        
        self._running = True
        
        # Start exchange clients
        await self._start_binance()
        await self._start_okx()
    
    async def stop(self):
        """Stop the market data service"""
        self._running = False
        
        # Stop exchange clients
        if self.binance_client:
            await self.binance_client.disconnect()
        if self.okx_client:
            await self.okx_client.disconnect()
    
    async def _start_binance(self):
        """Start Binance WebSocket client"""
        self.binance_client = BinanceWebSocket(symbols=SYMBOLS)
        self.binance_client.set_trade_callback(self._handle_trade)
        self.binance_client.set_orderbook_callback(self._handle_binance_orderbook)
        asyncio.create_task(self.binance_client.connect())
    
    async def _start_okx(self):
        """Start OKX WebSocket client"""
        self.okx_client = OKXWebSocket(symbols=SYMBOLS)
        self.okx_client.set_trade_callback(self._handle_trade)
        self.okx_client.set_orderbook_callback(self._handle_okx_orderbook)
        asyncio.create_task(self.okx_client.connect())
    
    async def _handle_trade(self, trade: Trade):
        """Handle incoming trade from exchanges"""
        # Update price precision
        self.price_formatter.update_precision(trade.symbol, trade.price)
        
        # Process EWMA
        ewma = self.ewma_processor.process_trade(trade)
        await self._broadcast_ewma(ewma)
        
        # Process klines for all intervals
        for interval_name, processor in self.kline_processors.items():
            kline = processor.process_trade(trade)
            if kline:
                await self._broadcast_kline(kline, interval_name)
        
        # Broadcast trade
        await self._broadcast_trade(trade)
    
    async def _handle_binance_orderbook(self, symbol: str, best_bid, best_ask):
        """Handle incoming orderbook update from Binance"""
        await self._process_orderbook(symbol, "binance", best_bid.price, best_ask.price)
    
    async def _handle_okx_orderbook(self, symbol: str, best_bid, best_ask):
        """Handle incoming orderbook update from OKX"""
        await self._process_orderbook(symbol, "okx", best_bid.price, best_ask.price)
    
    async def _process_orderbook(self, symbol: str, exchange: str, bid: float, ask: float):
        """Process orderbook update and broadcast to clients"""
        # Update price precision
        self.price_formatter.update_precision(symbol, bid)
        self.price_formatter.update_precision(symbol, ask)
        
        # Create OrderBookLevel objects
        bid_level = OrderBookLevel(price=bid, quantity=0.0, exchange=exchange)
        ask_level = OrderBookLevel(price=ask, quantity=0.0, exchange=exchange)
        
        # Update best touch aggregator
        self.best_touch_aggregator.update_orderbook(symbol, bid_level, ask_level)
        
        # Get and broadcast best touch
        best_touch = self.best_touch_aggregator.get_best_touch(symbol, exchange_filter="all")
        if best_touch:
            await self._broadcast_best_touch(best_touch)
    
    async def _broadcast_trade(self, trade: Trade):
        """Broadcast trade to subscribed clients"""
        data = {
            "symbol": trade.symbol,
            "exchange": trade.exchange,
            "price": trade.price,
            "quantity": trade.quantity,
            "timestamp": trade.timestamp.timestamp() if hasattr(trade.timestamp, 'timestamp') else trade.timestamp
        }
        await self.ws_manager.broadcast("trade", trade.symbol, trade.exchange, data)
    
    async def _broadcast_kline(self, kline: Kline, interval: str):
        """Broadcast kline to subscribed clients"""
        data = {
            "symbol": kline.symbol,
            "exchange": kline.exchange,
            "interval": interval,
            "open": kline.open,
            "high": kline.high,
            "low": kline.low,
            "close": kline.close,
            "volume": kline.volume,
            "open_time": kline.open_time.timestamp() if hasattr(kline.open_time, 'timestamp') else kline.open_time,
            "close_time": kline.close_time.timestamp() if hasattr(kline.close_time, 'timestamp') else kline.close_time
        }
        await self.ws_manager.broadcast("kline", kline.symbol, kline.exchange, data, interval)
    
    async def _broadcast_ewma(self, ewma: EWMA):
        """Broadcast EWMA to subscribed clients"""
        data = {
            "symbol": ewma.symbol,
            "exchange": ewma.exchange,
            "value": ewma.value,
            "timestamp": ewma.timestamp.timestamp() if hasattr(ewma.timestamp, 'timestamp') else ewma.timestamp
        }
        await self.ws_manager.broadcast("ewma", ewma.symbol, ewma.exchange, data)
    
    async def _broadcast_best_touch(self, best_touch: BestTouch):
        """Broadcast best touch to subscribed clients"""
        # Get precision (returns tuple of (price_precision, quantity_precision))
        price_precision, _ = self.price_formatter.get_precision(best_touch.symbol)
        
        data = {
            "symbol": best_touch.symbol,
            "bid_price": round(best_touch.best_bid_price, price_precision),
            "bid_exchange": best_touch.best_bid_exchange,
            "ask_price": round(best_touch.best_ask_price, price_precision),
            "ask_exchange": best_touch.best_ask_exchange,
            "spread": round(best_touch.best_ask_price - best_touch.best_bid_price, price_precision),
            "timestamp": best_touch.timestamp.timestamp() if hasattr(best_touch.timestamp, 'timestamp') else best_touch.timestamp
        }
        
        # Broadcast to "all" exchange filter since best touch is cross-exchange
        await self.ws_manager.broadcast("best_touch", best_touch.symbol, "all", data)
    
    def get_available_symbols(self) -> list[str]:
        """Get list of available symbols"""
        return SYMBOLS.copy()
    
    def get_available_exchanges(self) -> list[str]:
        """Get list of available exchanges"""
        return ["binance", "okx"]
    
    def get_available_intervals(self) -> list[str]:
        """Get list of available kline intervals"""
        return list(KLINE_INTERVALS.keys())
