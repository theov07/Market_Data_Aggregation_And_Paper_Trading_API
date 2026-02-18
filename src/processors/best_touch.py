"""
Best Touch aggregator - finds best bid/ask across multiple exchanges
"""
from datetime import datetime
from typing import Dict, Optional
from src.data.models import OrderBookLevel, BestTouch


class BestTouchAggregator:
    """
    Aggregates order book data from multiple exchanges to find the best bid and ask.
    
    Best bid = highest bid price across all exchanges
    Best ask = lowest ask price across all exchanges
    """
    
    def __init__(self):
        # Store latest order book levels for each symbol/exchange
        # Key: (symbol, exchange) -> (bid, ask)
        self.order_books: Dict[tuple, tuple[OrderBookLevel, OrderBookLevel]] = {}
        
    def _get_key(self, symbol: str, exchange: str) -> tuple:
        """Get key for storing order book"""
        return (symbol, exchange)
    
    def update_orderbook(self, symbol: str, bid: OrderBookLevel, ask: OrderBookLevel):
        """
        Update order book levels for a symbol/exchange.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            bid: Best bid level from this exchange
            ask: Best ask level from this exchange
        """
        key = self._get_key(symbol, bid.exchange)
        self.order_books[key] = (bid, ask)
    
    def get_best_touch(self, symbol: str, exchange_filter: str = "all") -> Optional[BestTouch]:
        """
        Get the best touch (best bid and ask) for a symbol.
        
        Args:
            symbol: Trading pair symbol
            exchange_filter: "all", "binance", or "okx"
            
        Returns:
            BestTouch object with the best bid/ask across filtered exchanges,
            or None if no data available
        """
        # Filter order books by symbol and exchange
        relevant_books = {}
        for (s, e), (bid, ask) in self.order_books.items():
            if s != symbol:
                continue
            if exchange_filter != "all" and e != exchange_filter:
                continue
            relevant_books[e] = (bid, ask)
        
        if not relevant_books:
            return None
        
        # Find best bid (highest price)
        best_bid = None
        best_bid_exchange = None
        for exchange, (bid, ask) in relevant_books.items():
            if bid.price > 0 and (best_bid is None or bid.price > best_bid.price):
                best_bid = bid
                best_bid_exchange = exchange
        
        # Find best ask (lowest price)
        best_ask = None
        best_ask_exchange = None
        for exchange, (bid, ask) in relevant_books.items():
            if ask.price > 0 and (best_ask is None or ask.price < best_ask.price):
                best_ask = ask
                best_ask_exchange = exchange
        
        # Both best bid and ask must exist
        if best_bid is None or best_ask is None:
            return None
        
        return BestTouch(
            symbol=symbol,
            best_bid_price=best_bid.price,
            best_bid_quantity=best_bid.quantity,
            best_bid_exchange=best_bid_exchange,
            best_ask_price=best_ask.price,
            best_ask_quantity=best_ask.quantity,
            best_ask_exchange=best_ask_exchange,
            timestamp=datetime.now()
        )
    
    def get_all_symbols(self) -> set[str]:
        """Get all symbols we have data for"""
        return {symbol for symbol, _ in self.order_books.keys()}
