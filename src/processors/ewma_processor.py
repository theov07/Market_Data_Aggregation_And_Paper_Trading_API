"""
EWMA (Exponential Weighted Moving Average) processor
"""
import math
from datetime import datetime
from typing import Dict, Optional
from src.data.models import Trade, EWMA


class EWMAProcessor:
    """
    Calculates Exponential Weighted Moving Average of trade prices.
    
    The EWMA is calculated using the formula:
    EWMA_t = alpha * price_t + (1 - alpha) * EWMA_{t-1}
    
    where alpha = 1 - exp(-ln(2) / half_life)
    """
    
    def __init__(self, half_life_seconds: float):
        """
        Initialize EWMA processor.
        
        Args:
            half_life_seconds: Half-life parameter in seconds. 
                              Determines how quickly old observations decay.
        """
        self.half_life = half_life_seconds
        
        # Calculate decay factor alpha
        # alpha = 1 - exp(-ln(2) / half_life)
        self.alpha = 1 - math.exp(-math.log(2) / half_life_seconds)
        
        # Store current EWMA values: (symbol, exchange) -> (ewma_value, last_timestamp)
        self.ewma_values: Dict[tuple, tuple[float, datetime]] = {}
        
    def _get_key(self, symbol: str, exchange: str) -> tuple:
        """Get key for storing EWMA"""
        return (symbol, exchange)
    
    def _calculate_time_weighted_alpha(self, time_delta_seconds: float) -> float:
        """
        Calculate time-weighted alpha for irregular time intervals.
        
        For irregular intervals, we adjust alpha based on actual time elapsed:
        alpha_adjusted = 1 - exp(-ln(2) * time_delta / half_life)
        """
        if time_delta_seconds <= 0:
            return 0
        return 1 - math.exp(-math.log(2) * time_delta_seconds / self.half_life)
    
    def process_trade(self, trade: Trade) -> EWMA:
        """
        Process a trade and update EWMA.
        
        Args:
            trade: Trade object
            
        Returns:
            Updated EWMA object
        """
        key = self._get_key(trade.symbol, trade.exchange)
        
        # Get previous EWMA value if exists
        if key in self.ewma_values:
            prev_value, prev_timestamp = self.ewma_values[key]
            
            # Calculate time delta in seconds
            time_delta = (trade.timestamp - prev_timestamp).total_seconds()
            
            # Use time-weighted alpha for irregular intervals
            alpha = self._calculate_time_weighted_alpha(time_delta)
            
            # Update EWMA: EWMA_t = alpha * price + (1 - alpha) * EWMA_{t-1}
            new_value = alpha * trade.price + (1 - alpha) * prev_value
        else:
            # First trade: initialize EWMA with trade price
            new_value = trade.price
        
        # Store updated value
        self.ewma_values[key] = (new_value, trade.timestamp)
        
        # Return EWMA object
        return EWMA(
            symbol=trade.symbol,
            value=new_value,
            half_life=self.half_life,
            timestamp=trade.timestamp,
            exchange=trade.exchange
        )
    
    def get_current_ewma(self, symbol: str, exchange: str) -> Optional[EWMA]:
        """Get current EWMA value for a symbol/exchange"""
        key = self._get_key(symbol, exchange)
        if key in self.ewma_values:
            value, timestamp = self.ewma_values[key]
            return EWMA(
                symbol=symbol,
                value=value,
                half_life=self.half_life,
                timestamp=timestamp,
                exchange=exchange
            )
        return None
    
    def reset(self, symbol: Optional[str] = None, exchange: Optional[str] = None):
        """
        Reset EWMA values.
        
        Args:
            symbol: If provided, reset only this symbol
            exchange: If provided (with symbol), reset only this symbol/exchange combination
        """
        if symbol is None:
            # Reset all
            self.ewma_values.clear()
        elif exchange is None:
            # Reset all exchanges for this symbol
            keys_to_remove = [k for k in self.ewma_values.keys() if k[0] == symbol]
            for key in keys_to_remove:
                del self.ewma_values[key]
        else:
            # Reset specific symbol/exchange
            key = self._get_key(symbol, exchange)
            if key in self.ewma_values:
                del self.ewma_values[key]
