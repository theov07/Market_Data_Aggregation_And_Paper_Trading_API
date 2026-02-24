"""
Market data service - coordinates exchange connections and data processing

KLINE PERIODIC PUSH STRATEGY:
- Klines are broadcast at least once per second to subscribed clients
- If no trades arrive, the current (incomplete) candle is rebroadcast unchanged
- No empty candles are created - the last known state is always sent
- This ensures real-time updates without REST/historical data dependencies
"""
import asyncio
from typing import Dict
import logging

from config import SYMBOLS, KLINE_INTERVALS
from src.data.models import Trade, Kline, EWMA, BestTouch, OrderBookLevel
from src.exchanges.binance_ws import BinanceWebSocket
from src.exchanges.okx_ws import OKXWebSocket
from src.processors.kline_processor import KlineProcessor
from src.processors.ewma_processor import EWMAProcessor
from src.processors.best_touch import BestTouchAggregator
from src.utils.formatting import PriceFormatter
from .websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

class MarketDataService:
    """
    Main service for market data aggregation and broadcasting
    """
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.ws_manager = websocket_manager
        self.price_formatter = PriceFormatter()
        self.best_touch_aggregator = BestTouchAggregator()
        
        # Create processors for each interval
        self.kline_processors: Dict[str, KlineProcessor] = {}
        self._init_kline_processors()
        
        # EWMA processor pool: key = (symbol, exchange, half_life)
        self.ewma_processors: Dict[tuple, EWMAProcessor] = {}
        
        # Exchange clients
        self.binance_client: BinanceWebSocket | None = None
        self.okx_client: OKXWebSocket | None = None
        
        self._running = False
        self._kline_tick_task: asyncio.Task | None = None
        self._cleanup_counter = 0  # Counter for periodic cleanup
    
    def _init_kline_processors(self):
        """
        Initialize kline processors for each interval
        """
        for interval_name, seconds in KLINE_INTERVALS.items():
            self.kline_processors[interval_name] = KlineProcessor(interval_seconds=seconds)
    
    async def start(self):
        """
        Start the market data service
        """
        if self._running:
            return
        
        self._running = True
        
        # Start kline periodic push task
        self._kline_tick_task = asyncio.create_task(self._kline_tick_loop())
        
        # Start exchange clients
        await self._start_binance()
        await self._start_okx()
    
    async def stop(self):
        """
        Stop the market data service
        """
        self._running = False
        
        # Cancel kline tick task
        if self._kline_tick_task:
            self._kline_tick_task.cancel()
            try:
                await self._kline_tick_task
            except asyncio.CancelledError:
                pass
        
        # Stop exchange clients
        if self.binance_client:
            await self.binance_client.disconnect()
        if self.okx_client:
            await self.okx_client.disconnect()
    
    async def _start_binance(self):
        """
        Start Binance WebSocket client
        """
        self.binance_client = BinanceWebSocket(symbols=SYMBOLS)
        self.binance_client.set_trade_callback(self._handle_trade)
        self.binance_client.set_orderbook_callback(self._handle_binance_orderbook)
        asyncio.create_task(self.binance_client.connect())
    
    async def _start_okx(self):
        """
        Start OKX WebSocket client
        """
        self.okx_client = OKXWebSocket(symbols=SYMBOLS)
        self.okx_client.set_trade_callback(self._handle_trade)
        self.okx_client.set_orderbook_callback(self._handle_okx_orderbook)
        asyncio.create_task(self.okx_client.connect())
    
    async def _handle_trade(self, trade: Trade):
        """
        Handle incoming trade from exchanges
        """
        # Filter invalid trades
        if trade.price <= 0 or trade.quantity <= 0:
            return
        
        # Update price precision
        self.price_formatter.update_precision(trade.symbol, trade.price)
        
        # Process EWMA for all active half_life values subscribed to this symbol/exchange
        active_half_lives = self.ws_manager.get_active_ewma_half_lives(trade.symbol, trade.exchange)
        for half_life in active_half_lives:
            ewma = self._get_or_create_ewma_processor(trade.symbol, trade.exchange, half_life).process_trade(trade)
            await self._broadcast_ewma(ewma, half_life)
        
        # Process klines for all intervals
        for interval_name, processor in self.kline_processors.items():
            kline = processor.process_trade(trade)
            if kline:
                await self._broadcast_kline(kline, interval_name)
        
        # Broadcast trade
        await self._broadcast_trade(trade)
    
    async def _kline_tick_loop(self):
        """
        Periodic task that pushes current klines every second.
        
        Strategy: Rebroadcast current (incomplete) klines to all subscribers.
        If no trade has occurred, the candle is sent unchanged (no empty candles created).
        
        Also performs periodic cleanup of inactive EWMA processors every 60 seconds.
        """
        while self._running:
            try:
                await asyncio.sleep(1.0)
                await self._push_current_klines()
                
                # Cleanup EWMA processors every 60 seconds
                self._cleanup_counter += 1
                if self._cleanup_counter >= 60:
                    await self._cleanup_inactive_ewma_processors()
                    self._cleanup_counter = 0
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in kline tick loop: {e}")
    
    async def _push_current_klines(self):
        """
        Push all current klines to subscribed clients
        """
        active_subscriptions = self.ws_manager.get_active_kline_subscriptions()
        
        if not active_subscriptions:
            return
        
        # Group by interval for efficient processing
        for interval_name, processor in self.kline_processors.items():
            # Get all current klines from this processor
            current_klines = processor.get_all_current_klines()
            
            for key, kline in current_klines.items():
                symbol, exchange = key
                
                # Check if anyone is subscribed to this combination
                has_subscription = any(
                    (sub_symbol, sub_exchange, sub_interval) == (symbol, exchange, interval_name) or
                    (sub_symbol, sub_exchange, sub_interval) == (symbol, "all", interval_name)
                    for sub_symbol, sub_exchange, sub_interval in active_subscriptions
                )
                
                if has_subscription:
                    await self._broadcast_kline(kline, interval_name)
    
    async def _handle_binance_orderbook(self, symbol: str, best_bid, best_ask):
        """
        Handle incoming orderbook update from Binance
        """
        await self._process_orderbook(symbol, "binance", best_bid.price, best_ask.price)
    
    async def _handle_okx_orderbook(self, symbol: str, best_bid, best_ask):
        """
        Handle incoming orderbook update from OKX
        """
        await self._process_orderbook(symbol, "okx", best_bid.price, best_ask.price)
    
    async def _process_orderbook(self, symbol: str, exchange: str, bid: float, ask: float):
        """
        Process orderbook update and broadcast to clients
        """
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
    
    def _get_or_create_ewma_processor(self, symbol: str, exchange: str, half_life: float) -> EWMAProcessor:
        """
        Get or create EWMA processor for given symbol/exchange/half_life
        """
        key = (symbol, exchange, half_life)
        if key not in self.ewma_processors:
            self.ewma_processors[key] = EWMAProcessor(half_life_seconds=half_life)
        return self.ewma_processors[key]
    
    async def _cleanup_inactive_ewma_processors(self):
        """
        Remove EWMA processors that have no active subscribers.
        
        This prevents memory leaks when clients disconnect or change half_life values.
        Called periodically (every 60 seconds) from _kline_tick_loop.
        """
        # Get all active EWMA subscriptions from websocket manager
        active_keys = self.ws_manager.get_all_active_ewma_subscriptions()
        
        # Remove processors that are not in active subscriptions
        processors_before = len(self.ewma_processors)
        for key in list(self.ewma_processors.keys()):
            if key not in active_keys:
                del self.ewma_processors[key]
        
        processors_after = len(self.ewma_processors)
        if processors_before > processors_after:
            logger.info(
                f"Cleaned up {processors_before - processors_after} inactive EWMA processors "
                f"({processors_before} -> {processors_after})"
            )
    
    async def _broadcast_trade(self, trade: Trade):
        """
        Broadcast trade to subscribed clients
        """
        data = {
            "symbol": trade.symbol,
            "exchange": trade.exchange,
            "price": trade.price,
            "quantity": trade.quantity,
            "timestamp": trade.timestamp.timestamp() if hasattr(trade.timestamp, 'timestamp') else trade.timestamp
        }
        await self.ws_manager.broadcast("trade", trade.symbol, trade.exchange, data)
    
    async def _broadcast_kline(self, kline: Kline, interval: str):
        """
        Broadcast kline to subscribed clients
        """
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
    
    async def _broadcast_ewma(self, ewma: EWMA, half_life: float):
        """
        Broadcast EWMA to subscribed clients
        """
        data = {
            "symbol": ewma.symbol,
            "exchange": ewma.exchange,
            "value": ewma.value,
            "half_life": half_life,
            "timestamp": ewma.timestamp.timestamp() if hasattr(ewma.timestamp, 'timestamp') else ewma.timestamp
        }
        await self.ws_manager.broadcast_ewma("ewma", ewma.symbol, ewma.exchange, half_life, data)
    
    async def _broadcast_best_touch(self, best_touch: BestTouch):
        """
        Broadcast best touch to subscribed clients
        """
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
        
        await self.ws_manager.broadcast("best_touch", best_touch.symbol, "all", data)
    
    def get_available_symbols(self) -> list[str]:
        """
        Get list of available symbols
        """
        return SYMBOLS.copy()
    
    def get_available_exchanges(self) -> list[str]:
        """
        Get list of available exchanges
        """
        return ["binance", "okx"]
    
    def get_available_intervals(self) -> list[str]:
        """
        Get list of available kline intervals
        """
        return list(KLINE_INTERVALS.keys())
