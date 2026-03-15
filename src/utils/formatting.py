"""
Price formatting utilities with automatic precision detection
"""
from typing import Dict, Tuple


class PriceFormatter:
    """
    Intelligent price formatter that adapts precision based on observed prices.
    Maintains precision cache per symbol to ensure consistent formatting.
    """
    
    def __init__(self):
        # Cache: symbol -> (price_precision, quantity_precision)
        self._precision_cache: Dict[str, Tuple[int, int]] = {}
    
    @staticmethod
    def _detect_precision(value: float, min_decimals: int = 2, max_decimals: int = 8) -> int:
        """
        Detect the number of significant decimal places in a float value.
        
        Args:
            value: The value to analyze
            min_decimals: Minimum number of decimals to show
            max_decimals: Maximum number of decimals to check
            
        Returns:
            Number of decimal places needed
        """
        if value == 0:
            return min_decimals
        
        # Convert to string with max precision
        value_str = f"{value:.{max_decimals}f}"
        
        # Remove trailing zeros
        value_str = value_str.rstrip('0').rstrip('.')
        
        if '.' not in value_str:
            return min_decimals
        
        decimals = len(value_str.split('.')[1])
        return max(min_decimals, min(decimals, max_decimals))
    
    def update_precision(self, symbol: str, price: float, quantity: float = None):
        """
        Update precision cache for a symbol based on observed price/quantity.
        
        Args:
            symbol: Trading pair symbol
            price: Observed price
            quantity: Observed quantity (optional)
        """
        price_precision = self._detect_precision(price)
        
        # For quantity, we want more precision for small values
        if quantity is not None:
            quantity_precision = self._detect_precision(quantity, min_decimals=4, max_decimals=8)
        else:
            quantity_precision = 4
        
        # Update cache if we haven't seen this symbol or found more precision
        if symbol not in self._precision_cache:
            self._precision_cache[symbol] = (price_precision, quantity_precision)
        else:
            current_price_prec, current_qty_prec = self._precision_cache[symbol]
            # Keep the maximum precision observed
            self._precision_cache[symbol] = (
                max(price_precision, current_price_prec),
                max(quantity_precision, current_qty_prec)
            )
    
    def format_price(self, symbol: str, price: float) -> str:
        """
        Format a price with appropriate precision for the symbol.
        
        Args:
            symbol: Trading pair symbol
            price: Price to format
            
        Returns:
            Formatted price string
        """
        if symbol in self._precision_cache:
            precision = self._precision_cache[symbol][0]
        else:
            # Fallback: detect on the fly
            precision = self._detect_precision(price)
        
        return f"{price:.{precision}f}"
    
    def format_quantity(self, symbol: str, quantity: float) -> str:
        """
        Format a quantity with appropriate precision for the symbol.
        
        Args:
            symbol: Trading pair symbol
            quantity: Quantity to format
            
        Returns:
            Formatted quantity string
        """
        if symbol in self._precision_cache:
            precision = self._precision_cache[symbol][1]
        else:
            # Fallback: detect on the fly
            precision = self._detect_precision(quantity, min_decimals=4)
        
        return f"{quantity:.{precision}f}"
    
    def get_precision(self, symbol: str) -> Tuple[int, int]:
        """
        Get cached precision for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Tuple of (price_precision, quantity_precision)
        """
        return self._precision_cache.get(symbol, (2, 4))



