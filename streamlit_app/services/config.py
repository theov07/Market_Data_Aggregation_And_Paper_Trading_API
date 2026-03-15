"""
Re-export config symbols so services can do `from .config import WS_BASE`.
Supports both package-relative and sys.path-root import styles.
"""
try:
    from ..utils.config import API_BASE, WS_BASE, SYMBOLS, EXCHANGES, KLINE_INTERVALS
except ImportError:
    from utils.config import API_BASE, WS_BASE, SYMBOLS, EXCHANGES, KLINE_INTERVALS  # type: ignore[no-redef]

__all__ = ["API_BASE", "WS_BASE", "SYMBOLS", "EXCHANGES", "KLINE_INTERVALS"]
