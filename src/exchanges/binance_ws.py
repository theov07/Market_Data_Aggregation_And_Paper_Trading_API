"""
Binance WebSocket client for order book and trade data
"""
import asyncio
import json
import logging
import ssl
from datetime import datetime
from typing import Callable, List, Optional
import websockets

from src.data.models import Trade, OrderBookLevel

logger = logging.getLogger(__name__)


class BinanceWebSocket:
    """Handles WebSocket connections to Binance"""
    
    def __init__(self, symbols: List[str]):
        self.symbols = [s.lower() for s in symbols]
        self.ws = None
        self.running = False
        
        # Callbacks for different data types
        self.on_trade_callback: Optional[Callable] = None
        self.on_orderbook_callback: Optional[Callable] = None
        
    def set_trade_callback(self, callback: Callable):
        """Set callback for trade data"""
        self.on_trade_callback = callback
        
    def set_orderbook_callback(self, callback: Callable):
        """Set callback for order book data"""
        self.on_orderbook_callback = callback
    
    def _build_stream_url(self) -> str:
        """Build WebSocket URL for multiple streams (Futures)"""
        streams = []
        for symbol in self.symbols:
            streams.append(f"{symbol}@trade")
            streams.append(f"{symbol}@bookTicker")
        
        stream_names = "/".join(streams)
        return f"wss://fstream.binance.com/stream?streams={stream_names}"
    
    def _parse_trade(self, data: dict) -> Trade:
        """Parse Binance trade message"""
        return Trade(
            symbol=data["s"],
            price=float(data["p"]),
            quantity=float(data["q"]),
            side="sell" if data["m"] else "buy",  # m=true means buyer is maker (sell)
            timestamp=datetime.fromtimestamp(data["T"] / 1000),
            exchange="binance",
            trade_id=str(data["t"])
        )
    
    def _parse_orderbook(self, data: dict) -> tuple[OrderBookLevel, OrderBookLevel]:
        """Parse Binance book ticker (best bid/ask)"""
        best_bid = OrderBookLevel(
            price=float(data["b"]),
            quantity=float(data["B"]),
            exchange="binance"
        )
        best_ask = OrderBookLevel(
            price=float(data["a"]),
            quantity=float(data["A"]),
            exchange="binance"
        )
        return data["s"], best_bid, best_ask
    
    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            if "stream" not in data:
                return
            
            stream = data["stream"]
            payload = data["data"]
            
            # Handle trade stream
            if "@trade" in stream:
                trade = self._parse_trade(payload)
                if self.on_trade_callback:
                    await self.on_trade_callback(trade)
            
            # Handle order book ticker
            elif "@bookTicker" in stream:
                symbol, best_bid, best_ask = self._parse_orderbook(payload)
                if self.on_orderbook_callback:
                    await self.on_orderbook_callback(symbol, best_bid, best_ask)
                    
        except Exception as e:
            logger.error(f"Error handling Binance message: {e}")
    
    async def connect(self):
        """Connect to Binance WebSocket and start listening"""
        url = self._build_stream_url()
        self.running = True
        
        logger.info("Connecting to Binance...")
        
        # Disable SSL verification
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        while self.running:
            try:
                async with websockets.connect(url, ssl=ssl_context) as ws:
                    self.ws = ws
                    logger.info("Connected to Binance")
                    
                    async for message in ws:
                        if not self.running:
                            break
                        await self._handle_message(message)
                        
            except Exception as e:
                logger.error(f"Binance connection error: {e}")
                if self.running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self.running = False
        if self.ws:
            await self.ws.close()
