"""
Demo script to test WebSocket connections and data processors
"""
import asyncio
from datetime import datetime

from config import SYMBOLS
from src.exchanges.binance_ws import BinanceWebSocket
from src.exchanges.okx_ws import OKXWebSocket
from src.processors.kline_processor import KlineProcessor
from src.processors.ewma_processor import EWMAProcessor
from src.processors.best_touch import BestTouchAggregator
from src.utils.formatting import format_price, format_quantity, update_precision


class MarketDataDemo:
    """Demo class to test market data collection"""
    
    def __init__(self):
        # Initialize WebSocket clients
        self.binance_ws = BinanceWebSocket(SYMBOLS)
        self.okx_ws = OKXWebSocket(SYMBOLS)
        
        # Initialize processors
        self.kline_1s = KlineProcessor(interval_seconds=1)
        self.kline_10s = KlineProcessor(interval_seconds=10)
        self.kline_1m = KlineProcessor(interval_seconds=60)
        self.ewma_30s = EWMAProcessor(half_life_seconds=30)
        self.best_touch = BestTouchAggregator()
        
        # Counters for display
        self.trade_count = 0
        self.last_display = datetime.now()
        
    async def on_trade(self, trade):
        """Callback for trade data"""
        self.trade_count += 1
        
        # Update precision cache based on observed trade
        update_precision(trade.symbol, trade.price, trade.quantity)
        
        # Process trade through kline processors
        closed_1s = self.kline_1s.process_trade(trade)
        closed_10s = self.kline_10s.process_trade(trade)
        closed_1m = self.kline_1m.process_trade(trade)
        
        # Process trade through EWMA
        ewma = self.ewma_30s.process_trade(trade)
        
        # Display closed klines
        if closed_1s:
            print(f"\n[KLINE-1s CLOSED] {closed_1s.symbol} @ {closed_1s.exchange}")
            print(f"  O:{format_price(closed_1s.symbol, closed_1s.open)} H:{format_price(closed_1s.symbol, closed_1s.high)} L:{format_price(closed_1s.symbol, closed_1s.low)} C:{format_price(closed_1s.symbol, closed_1s.close)} V:{format_quantity(closed_1s.symbol, closed_1s.volume)}")
        
        # Display stats periodically
        now = datetime.now()
        if (now - self.last_display).total_seconds() >= 5:
            print(f"\n--- Stats: {self.trade_count} trades processed ---")
            
            # Show current klines for all symbols
            for symbol in SYMBOLS:
                current_1s = self.kline_1s.get_current_kline(symbol, "binance")
                if current_1s:
                    print(f"[Kline 1s] {symbol}@binance: O:{format_price(symbol, current_1s.open)} C:{format_price(symbol, current_1s.close)} V:{format_quantity(symbol, current_1s.volume)}")
            
            print()  # Empty line for readability
            
            # Show EWMA for all symbols
            for symbol in SYMBOLS:
                ewma = self.ewma_30s.get_current_ewma(symbol, "binance")
                if ewma:
                    print(f"[EWMA 30s] {symbol}@binance: {format_price(symbol, ewma.value)}")
            
            print()  # Empty line for readability
            
            # Show best touch for all symbols
            for symbol in SYMBOLS:
                best_touch = self.best_touch.get_best_touch(symbol, "all")
                if best_touch:
                    spread = best_touch.best_ask_price - best_touch.best_bid_price
                    
                    # Check for arbitrage opportunity (negative spread)
                    if spread < 0:
                        arbitrage_profit = abs(spread)
                        print(f"[Best Touch] {symbol}: Bid {format_price(symbol, best_touch.best_bid_price)}@{best_touch.best_bid_exchange} | Ask {format_price(symbol, best_touch.best_ask_price)}@{best_touch.best_ask_exchange} | ⚡ ARBITRAGE: +${format_price(symbol, arbitrage_profit)}")
                    else:
                        print(f"[Best Touch] {symbol}: Bid {format_price(symbol, best_touch.best_bid_price)}@{best_touch.best_bid_exchange} | Ask {format_price(symbol, best_touch.best_ask_price)}@{best_touch.best_ask_exchange} | Spread {format_price(symbol, spread)}")
            
            self.last_display = now
    
    async def on_orderbook(self, symbol, bid, ask):
        """Callback for order book updates"""
        self.best_touch.update_orderbook(symbol, bid, ask)
    
    async def run(self):
        """Run the demo"""
        # Set callbacks
        self.binance_ws.set_trade_callback(self.on_trade)
        self.binance_ws.set_orderbook_callback(self.on_orderbook)
        self.okx_ws.set_trade_callback(self.on_trade)
        self.okx_ws.set_orderbook_callback(self.on_orderbook)
        
        print("Starting market data collection...")
        print(f"Monitoring symbols: {SYMBOLS}")
        print("Press Ctrl+C to stop\n")
        
        # Run both WebSocket clients concurrently
        try:
            await asyncio.gather(
                self.binance_ws.connect(),
                self.okx_ws.connect()
            )
        except KeyboardInterrupt:
            print("\nStopping...")
            await self.binance_ws.disconnect()
            await self.okx_ws.disconnect()


if __name__ == "__main__":
    demo = MarketDataDemo()
    asyncio.run(demo.run())
