"""
Market Data Aggregation & Paper Trading — Streamlit Dashboard
Entry point: streamlit run streamlit_app/app.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

from utils.theme import inject_css, page_setup
from utils.state import init
from services.api_client import health_check, get_info
from services.data_adapter import MarketDataStore
from services.server_manager import is_running, start_server, AUTO_STOP_SECONDS

page_setup("Paper Trading Dashboard")
inject_css()
init()

# ── Auto-start backend if not already running ──────────────────────────────────
if "server_autostart_done" not in st.session_state:
    st.session_state["server_autostart_done"] = True
    if not is_running():
        start_server()  # fire-and-forget; result visible via health_check()

# Shared market data store — one instance for all pages
if "market_store" not in st.session_state:
    st.session_state["market_store"] = MarketDataStore()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Paper Trading API")
    st.markdown("---")

    backend_ok = health_check()
    color = "#22c55e" if backend_ok else "#ef4444"
    label = "Backend Online" if backend_ok else "Backend Offline"
    st.markdown(
        f'<span style="color:{color};font-weight:600">{label}</span>',
        unsafe_allow_html=True,
    )
    if not backend_ok:
        st.caption("Start: `SECRET_KEY=$(openssl rand -hex 32) python run_server.py`")
    else:
        st.caption(f"⏱ Auto-stops after {AUTO_STOP_SECONDS // 60} min")

    username = st.session_state.get("username")
    if username:
        st.markdown(f"Logged in as **{username}**")
    else:
        st.caption("Not logged in")

    st.markdown("---")

    if backend_ok:
        info, _ = get_info()
        if info:
            pairs    = ", ".join(info.get("trading_pairs", []))
            exchanges = ", ".join(info.get("exchanges", []))
            st.caption(f"Symbols: {pairs}")
            st.caption(f"Exchanges: {exchanges}")

# ── Home ───────────────────────────────────────────────────────────────────────
st.title("Market Data Aggregation & Paper Trading")
st.markdown("Navigate using the sidebar. Use **Overview** to log in and connect to the WebSocket.")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Getting started")
    st.markdown("""
1. **Start the backend**
   ```bash
   SECRET_KEY=$(openssl rand -hex 32) python run_server.py
   ```
2. **Register or login** — Overview page
3. **Connect to WebSocket & subscribe** — Overview page
4. **Deposit funds** — Portfolio page (e.g. 10 000 USDT)
5. **Watch live prices** — Market Data page
6. **Place orders** — Orders page
    """)

with col2:
    st.subheader("Pages")
    st.markdown("""
| Page | Purpose |
|---|---|
| Overview | Login, WebSocket, diagnostics |
| Market Data | Live WS feeds |
| Order Book | Best bid/ask |
| Orders | Place & manage |
| Portfolio | Balances, deposit |
    """)
