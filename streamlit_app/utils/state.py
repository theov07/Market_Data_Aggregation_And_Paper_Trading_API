"""
Session-state helpers.
"""
import streamlit as st


def init():
    defaults = {
        "token":    None,
        "username": None,
        "orders":   [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def is_authenticated() -> bool:
    return bool(st.session_state.get("token"))


def set_auth(token: str, username: str):
    st.session_state["token"] = token
    st.session_state["username"] = username


def clear_auth():
    st.session_state["token"] = None
    st.session_state["username"] = None


def upsert_order(order: dict):
    """Insert or update an order in the session list by token_id."""
    orders: list = st.session_state.setdefault("orders", [])
    for i, o in enumerate(orders):
        if o.get("token_id") == order.get("token_id"):
            orders[i] = order
            return
    orders.append(order)


def apply_ws_order_update(data: dict):
    """Merge an order_update WS payload into session orders."""
    orders: list = st.session_state.setdefault("orders", [])
    tid = data.get("token_id")
    for i, o in enumerate(orders):
        if o.get("token_id") == tid:
            orders[i] = {**o, **data}
            return
    orders.append(data)
