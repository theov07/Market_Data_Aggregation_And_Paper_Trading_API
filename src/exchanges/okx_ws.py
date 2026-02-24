"""
OKX WebSocket client for order book and trade data
"""
import asyncio
import json
import logging
import ssl
from datetime import datetime
from typing import Callable, List, Optional
import websockets

from src.data.models import Trade, OrderBookLevel
from config import OKX_WS_BASE, MARKET_TYPE

logger = logging.getLogger(__name__)


class OKXWebSocket:
    """Handles WebSocket connections to OKX"""
    
    def __init__(self, symbols: List[str]):
        # OKX uses different format: BTC-USDT instead of BTCUSDT
        self.symbols = [self._format_symbol(s) for s in symbols]
        self.ws = None
        self.running = False
        
        # Callbacks for different data types
        self.on_trade_callback: Optional[Callable] = None
        self.on_orderbook_callback: Optional[Callable] = None
        
    def _format_symbol(self, symbol: str) -> str:
        """Convert BTCUSDT to OKX format (BTC-USDT-SWAP for futures, BTC-USDT for spot)"""
        # Simple conversion for common pairs
        if symbol.endswith("USDT"):
            base = symbol[:-4]
            if MARKET_TYPE == "futures":
                return f"{base}-USDT-SWAP"
            else:
                return f"{base}-USDT"
        return symbol
    
    def _unformat_symbol(self, symbol: str) -> str:
        """Convert BTC-USDT-SWAP back to BTCUSDT"""
        # Remove -SWAP suffix for futures
        if symbol.endswith("-SWAP"):
            symbol = symbol[:-5]  # Remove "-SWAP"
        # Remove remaining dashes
        return symbol.replace("-", "")
        
    def set_trade_callback(self, callback: Callable):
        """Set callback for trade data"""
        self.on_trade_callback = callback
        
    def set_orderbook_callback(self, callback: Callable):
        """Set callback for order book data"""
        self.on_orderbook_callback = callback
    
    def _build_subscription_message(self) -> dict:
        """Build subscription message for OKX"""
        args = []
        for symbol in self.symbols:
            args.append({"channel": "trades", "instId": symbol})
            args.append({"channel": "bbo-tbt", "instId": symbol})  # Best bid/offer
        
        return {
            "op": "subscribe",
            "args": args
        }
    
    def _parse_trade(self, data: dict) -> Trade:
        """Parse OKX trade message"""
        return Trade(
            symbol=self._unformat_symbol(data["instId"]),
            price=float(data["px"]),
            quantity=float(data["sz"]),
            side=data["side"],
            timestamp=datetime.fromtimestamp(int(data["ts"]) / 1000),
            exchange="okx",
            trade_id=data["tradeId"]
        )
    
    def _parse_orderbook(self, data: dict) -> tuple[str, OrderBookLevel, OrderBookLevel]:
        """Parse OKX best bid/offer"""
        symbol = self._unformat_symbol(data["instId"])
        
        best_bid = OrderBookLevel(
            price=float(data["bids"][0][0]) if data["bids"] else 0.0,
            quantity=float(data["bids"][0][1]) if data["bids"] else 0.0,
            exchange="okx"
        )
        best_ask = OrderBookLevel(
            price=float(data["asks"][0][0]) if data["asks"] else 0.0,
            quantity=float(data["asks"][0][1]) if data["asks"] else 0.0,
            exchange="okx"
        )
        return symbol, best_bid, best_ask
    
    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            # Handle subscription confirmation
            if data.get("event") == "subscribe":
                return
            
            # Handle subscription errors
            if data.get("event") == "error":
                logger.error(f"OKX subscription error: {data}")
                return
            
            # Handle data messages
            if "arg" not in data or "data" not in data:
                return
            
            channel = data["arg"]["channel"]
            
            # Handle trades
            if channel == "trades":
                for trade_data in data["data"]:
                    if "instId" not in trade_data:
                        continue
                    trade = self._parse_trade(trade_data)
                    if self.on_trade_callback:
                        await self.on_trade_callback(trade)
            
            # Handle best bid/offer
            elif channel == "bbo-tbt":
                # For bbo-tbt, instId is in arg, not in data elements
                inst_id = data["arg"].get("instId")
                if not inst_id:
                    return
                
                symbol = self._unformat_symbol(inst_id)
                
                for book_data in data["data"]:
                    # Parse orderbook without instId in book_data
                    best_bid = OrderBookLevel(
                        price=float(book_data["bids"][0][0]) if book_data.get("bids") else 0.0,
                        quantity=float(book_data["bids"][0][1]) if book_data.get("bids") else 0.0,
                        exchange="okx"
                    )
                    best_ask = OrderBookLevel(
                        price=float(book_data["asks"][0][0]) if book_data.get("asks") else 0.0,
                        quantity=float(book_data["asks"][0][1]) if book_data.get("asks") else 0.0,
                        exchange="okx"
                    )
                    
                    if self.on_orderbook_callback:
                        await self.on_orderbook_callback(symbol, best_bid, best_ask)
                        
        except Exception as e:
            logger.error(f"Error handling OKX message: {e}")
    OKX_WS_BASE
    async def connect(self):
        """Connect to OKX WebSocket and start listening"""
        url = "wss://ws.okx.com:8443/ws/v5/public"
        self.running = True
        
        # Disable SSL verification
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        while self.running:
            try:
                async with websockets.connect(url, ssl=ssl_context) as ws:
                    self.ws = ws
                    
                    # Send subscription message
                    sub_msg = self._build_subscription_message()
                    await ws.send(json.dumps(sub_msg))
                    
                    async for message in ws:
                        if not self.running:
                            break
                        await self._handle_message(message)
                        
            except Exception as e:
                logger.error(f"OKX connection error: {e}")
                if self.running:
                    await asyncio.sleep(5)
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self.running = False
        if self.ws:
            await self.ws.close()
