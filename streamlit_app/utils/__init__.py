"""
`__init__.py` for utils package — re-exports convenience symbols.
"""
from .config import API_BASE, WS_BASE, SYMBOLS, EXCHANGES, KLINE_INTERVALS, DATA_TYPES
from .state import init, is_authenticated, set_auth, clear_auth, upsert_order, apply_ws_order_update
from .theme import inject_css, page_setup
from .formatting import fmt_price, fmt_qty, side_badge, status_badge

__all__ = [
    "API_BASE", "WS_BASE", "SYMBOLS", "EXCHANGES", "KLINE_INTERVALS", "DATA_TYPES",
    "init", "is_authenticated", "set_auth", "clear_auth", "upsert_order", "apply_ws_order_update",
    "inject_css", "page_setup",
    "fmt_price", "fmt_qty", "side_badge", "status_badge",
]
