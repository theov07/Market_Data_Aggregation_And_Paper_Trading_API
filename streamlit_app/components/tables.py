"""
Styled dataframe / table components.
"""
from datetime import datetime, timezone
import pandas as pd
import streamlit as st


def _fmt_ts(ts) -> str:
    """Convert a Unix epoch float (or None) to a UTC time string HH:MM:SS."""
    if ts is None:
        return ""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%H:%M:%S UTC")
    except (TypeError, ValueError, OSError):
        return str(ts)


def orders_table(orders: list[dict]):
    """Render the session orders list as a styled dataframe."""
    if not orders:
        st.info("No orders tracked this session.")
        return

    rows = []
    for o in orders:
        rows.append({
            "Token ID":      o.get("token_id", ""),
            "Symbol":        o.get("symbol", ""),
            "Side":          o.get("side", "").upper(),
            "Type":          o.get("order_type", ""),
            "Price":         o.get("price"),
            "Qty":           o.get("quantity"),
            "Filled Qty":    o.get("filled_quantity"),
            "Status":        o.get("status", "").upper(),
            "Created":       o.get("created_at", ""),
            "Executed":      o.get("executed_at", ""),
        })

    df = pd.DataFrame(rows)

    def colour_side(val):
        if val == "BUY":
            return "color: #22c55e"
        if val == "SELL":
            return "color: #ef4444"
        return ""

    def colour_status(val):
        m = {"OPEN": "color:#3b82f6", "FILLED": "color:#22c55e",
             "CANCELLED": "color:#f97316", "REJECTED": "color:#ef4444"}
        return m.get(val, "")

    styled = (
        df.style
        .map(colour_side, subset=["Side"])
        .map(colour_status, subset=["Status"])
        .format({
            "Price":      lambda v: f"{v:,.2f}" if v is not None else "—",
            "Qty":        lambda v: f"{v:.4f}" if v is not None else "—",
            "Filled Qty": lambda v: f"{v:.4f}" if v is not None else "—",
        })
    )
    st.dataframe(styled, width="stretch", hide_index=True)


def balances_table(balances: list[dict]):
    if not balances:
        st.info("No balance data available.")
        return
    df = pd.DataFrame(balances)
    display_cols = [c for c in ["asset", "total", "available", "reserved"] if c in df.columns]
    st.dataframe(
        df[display_cols].style.format({
            "total":     "{:,.4f}",
            "available": "{:,.4f}",
            "reserved":  "{:,.4f}",
        }),
        width="stretch",
        hide_index=True,
    )


def trades_table(trades: list, max_rows: int = 50):
    if not trades:
        st.info("No trades received yet.")
        return
    rows = [
        {
            "Time (UTC)": _fmt_ts(t.timestamp),
            "Exchange":   t.exchange,
            "Symbol":     t.symbol,
            "Side":       t.side.upper(),
            "Price":      t.price,
            "Qty":        t.quantity,
        }
        for t in reversed(trades[-max_rows:])
    ]
    df = pd.DataFrame(rows)

    def colour_side(val):
        return "color: #22c55e" if val == "BUY" else "color: #ef4444"

    styled = (
        df.style
        .map(colour_side, subset=["Side"])
        .format({"Price": "{:,.2f}", "Qty": "{:.4f}"})
    )
    st.dataframe(styled, width="stretch", hide_index=True, column_order=["Time (UTC)", "Exchange", "Symbol", "Side", "Price", "Qty"])


def best_touch_table(store_bt: dict):
    """
    store_bt: {symbol: {exchange: BestTouchSnapshot}}
    """
    rows = []
    for sym, exchanges in store_bt.items():
        for snap in exchanges.values():
            rows.append({
                "Symbol":       sym,
                "Bid Price":    snap.best_bid_price,
                "Bid Exch":     snap.bid_exchange,
                "Ask Price":    snap.best_ask_price,
                "Ask Exch":     snap.ask_exchange,
                "Spread":       snap.spread,
                "Mid":          snap.mid,
                "Updated (UTC)": _fmt_ts(snap.timestamp),
            })
    if not rows:
        st.info("No best-touch data yet — subscribe via the sidebar.")
        return
    df = pd.DataFrame(rows)
    st.dataframe(
        df.style.format({
            "Bid Price": "{:,.2f}",
            "Ask Price": "{:,.2f}",
            "Spread":    "{:.4f}",
            "Mid":       "{:,.2f}",
        }),
        width="stretch",
        hide_index=True,
        column_order=["Symbol", "Bid Price", "Bid Exch", "Ask Price", "Ask Exch", "Spread", "Mid", "Updated (UTC)"],
    )
