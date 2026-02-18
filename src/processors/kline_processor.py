"""
Kline (candlestick) processor that aggregates trades into OHLCV candles
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
from src.data.models import Trade, Kline


class KlineProcessor:
    """Processes trades to generate live klines/candlesticks"""
    
    def __init__(self, interval_seconds: int):
        self.interval_seconds = interval_seconds
        
        # Store current klines: (symbol, exchange) -> Kline
        self.current_klines: Dict[tuple, Kline] = {}
        
    def _get_candle_start_time(self, timestamp: datetime) -> datetime:
        """Get the start time of the candle containing this timestamp"""
        # Round down to the interval
        ts_seconds = int(timestamp.timestamp())
        candle_start = (ts_seconds // self.interval_seconds) * self.interval_seconds
        return datetime.fromtimestamp(candle_start)
    
    def _get_key(self, symbol: str, exchange: str) -> tuple:
        """Get key for storing kline"""
        return (symbol, exchange)
    
    def process_trade(self, trade: Trade) -> Optional[Kline]:
        """
        Process a trade and update the current kline.
        Returns the completed kline if the candle just closed, None otherwise.
        """
        key = self._get_key(trade.symbol, trade.exchange)
        candle_start = self._get_candle_start_time(trade.timestamp)
        candle_end = candle_start + timedelta(seconds=self.interval_seconds)
        
        # Check if we have a current kline for this symbol/exchange
        current_kline = self.current_klines.get(key)
        
        # If no current kline or the trade is in a new candle period
        if current_kline is None or current_kline.open_time != candle_start:
            # If we had a previous kline, mark it as closed
            completed_kline = None
            if current_kline is not None:
                current_kline.is_closed = True
                completed_kline = current_kline
            
            # Create new kline
            new_kline = Kline(
                symbol=trade.symbol,
                interval=f"{self.interval_seconds}s",
                open_time=candle_start,
                close_time=candle_end,
                open=trade.price,
                high=trade.price,
                low=trade.price,
                close=trade.price,
                volume=trade.quantity,
                exchange=trade.exchange,
                is_closed=False
            )
            self.current_klines[key] = new_kline
            
            return completed_kline
        else:
            # Update existing kline
            current_kline.high = max(current_kline.high, trade.price)
            current_kline.low = min(current_kline.low, trade.price)
            current_kline.close = trade.price
            current_kline.volume += trade.quantity
            
            return None
    
    def get_current_kline(self, symbol: str, exchange: str) -> Optional[Kline]:
        """Get the current (incomplete) kline for a symbol/exchange"""
        key = self._get_key(symbol, exchange)
        return self.current_klines.get(key)
    
    def get_all_current_klines(self) -> Dict[tuple, Kline]:
        """Get all current klines"""
        return self.current_klines.copy()
