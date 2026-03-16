"""
Market Data Aggregation & Paper Trading — Streamlit Dashboard
Entry point: streamlit run streamlit_app/app.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

from utils.theme import inject_css, page_setup
from utils.state import init, is_authenticated
from services.api_client import health_check, get_info
from services.data_adapter import MarketDataStore
from services.ws_client import get_client

page_setup("Paper Trading Dashboard")
inject_css()
init()

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
        if os.name == "nt":
            st.caption('Start (PowerShell): `$env:SECRET_KEY = "your-secure-secret-key-min-32-chars"; python run_server.py`')
        else:
            st.caption("Start: `SECRET_KEY=$(openssl rand -hex 32) python run_server.py`")

    username = st.session_state.get("username")
    if username:
        st.markdown(f"Logged in as **{username}**")
    else:
        st.caption("Not logged in")

    client = get_client()
    auth_label = "Authenticated ✅" if is_authenticated() else "Authenticated ❌"
    ws_label = "WebSocket Connected ✅" if client.connected else "WebSocket Disconnected ❌"
    st.caption(auth_label)
    st.caption(ws_label)

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
    start_cmd = (
        '$env:SECRET_KEY = "your-secure-secret-key-min-32-chars"; python run_server.py'
        if os.name == "nt"
        else "SECRET_KEY=$(openssl rand -hex 32) python run_server.py"
    )
    backend_step = (
        "1. **Backend already running** ✅"
        if backend_ok
        else "1. **Start the backend**\n   ```bash\n   {start_cmd}\n   ```".format(start_cmd=start_cmd)
    )
    st.markdown("""
{backend_step}
2. **Register or login** — Overview page
3. **Connect to WebSocket & subscribe** — Overview page
4. **Deposit funds** — Portfolio page (e.g. 10 000 USDT)
5. **Watch live prices** — Market Data page
6. **Place orders** — Orders page
    """.format(backend_step=backend_step))

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
