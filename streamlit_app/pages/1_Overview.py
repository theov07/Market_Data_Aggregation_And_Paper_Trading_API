import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json, time
import streamlit as st
from utils.theme import page_setup, inject_css
from utils.state import init, is_authenticated, set_auth, clear_auth, apply_ws_order_update
from utils.config import SYMBOLS, EXCHANGES, DATA_TYPES, KLINE_INTERVALS
from services.api_client import health_check, get_info, login, register, get_balance
from services.ws_client import get_client, reset_client
from services.server_manager import is_running, start_server, stop_server
from components.status import ws_message_log

page_setup("Home")
inject_css()
init()

if "market_store" not in st.session_state:
    from services.data_adapter import MarketDataStore
    st.session_state["market_store"] = MarketDataStore()
store = st.session_state["market_store"]

client = get_client()

# ── Sidebar: Backend server ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Backend Server")
    srv_running = is_running()
    srv_color = "#22c55e" if srv_running else "#ef4444"
    srv_label = "Running" if srv_running else "Stopped"
    st.markdown(f'<span style="color:{srv_color};font-weight:600">{srv_label}</span>', unsafe_allow_html=True)
    col_srv1, col_srv2 = st.columns(2)
    with col_srv1:
        if st.button("Start", width="stretch", disabled=srv_running):
            with st.spinner("Starting…"):
                ok, msg = start_server()
            if ok:
                st.success(msg)
            else:
                st.error(msg)
            st.rerun()
    with col_srv2:
        if st.button("Stop", width="stretch", disabled=not srv_running):
            ok, msg = stop_server()
            if ok:
                st.info(msg)
            else:
                st.error(msg)
            st.rerun()

    st.markdown("---")
    st.markdown("### WebSocket")
    token = st.session_state.get("token") if is_authenticated() else None
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Connect", width="stretch", disabled=client.connected):
            client.connect(token)
            st.rerun()
    with col_b:
        if st.button("Reset", width="stretch"):
            reset_client()
            st.rerun()
    color = "#22c55e" if client.connected else "#ef4444"
    label = "Connected" if client.connected else "Disconnected"
    st.markdown(f'<span style="color:{color};font-weight:600">{label}</span>', unsafe_allow_html=True)
    if client.error:
        st.caption(f"Error: {client.error}")

    st.markdown("---")
    st.markdown("### Subscribe")
    dtype    = st.selectbox("Data type", DATA_TYPES)
    sym      = st.selectbox("Symbol", SYMBOLS)
    exc_default = EXCHANGES.index("all") if dtype == "best_touch" else 0
    exc      = st.selectbox("Exchange", EXCHANGES, index=exc_default, key=f"exc_{dtype}")
    interval = None
    hl       = None
    if dtype == "kline":
        interval = st.selectbox("Interval", KLINE_INTERVALS)
    if dtype == "ewma":
        hl = st.number_input("Half-life (s)", value=10.0, min_value=1.0)
    if st.button("Subscribe", width="stretch"):
        if not client.connected:
            client.connect(token)
            time.sleep(1.2)
        client.subscribe(dtype, sym, exc, interval, hl)
        st.rerun()

    st.markdown("---")
    refresh = st.slider("Auto-refresh (s)", 1, 10, 2)

# ── Drain WS messages ──────────────────────────────────────────────────────────
new_msgs = client.drain()
for msg in new_msgs:
    store.process_message(msg)
    if msg.get("type") == "order_update":
        apply_ws_order_update(msg)

# ── Status bar ─────────────────────────────────────────────────────────────────
backend_ok = health_check()
c1, c2, c3 = st.columns(3)
c1.markdown(
    f'<div class="kpi-card"><div class="kpi-label">Backend</div>'
    f'<div class="kpi-value" style="color:{"#22c55e" if backend_ok else "#ef4444"}">'
    f'{"Online" if backend_ok else "Offline"}</div></div>',
    unsafe_allow_html=True,
)
c2.markdown(
    f'<div class="kpi-card"><div class="kpi-label">WebSocket</div>'
    f'<div class="kpi-value" style="color:{"#22c55e" if client.connected else "#6e7681"}">'
    f'{"Connected" if client.connected else "Disconnected"}</div></div>',
    unsafe_allow_html=True,
)
c3.markdown(
    f'<div class="kpi-card"><div class="kpi-label">Logged in as</div>'
    f'<div class="kpi-value">{st.session_state.get("username") or "—"}</div></div>',
    unsafe_allow_html=True,
)

if not backend_ok:
    st.error("Backend is offline. Start it with: `SECRET_KEY=$(openssl rand -hex 32) python run_server.py`")
    st.stop()

st.divider()

# ── Auth ───────────────────────────────────────────────────────────────────────
if is_authenticated():
    col_info, col_logout = st.columns([4, 1])
    with col_logout:
        if st.button("Logout", width="stretch"):
            clear_auth()
            st.rerun()

    # Balance snapshot
    bal, _ = get_balance(st.session_state["token"])
    if bal:
        assets = bal.get("balances", [])
        if assets:
            st.subheader("Balances")
            cols = st.columns(min(len(assets), 5))
            for col, a in zip(cols, assets):
                col.markdown(
                    f'<div class="kpi-card">'
                    f'<div class="kpi-label">{a["asset"]}</div>'
                    f'<div class="kpi-value">{a["available"]:,.4f}</div>'
                    f'<div class="kpi-sub">total {a["total"]:,.4f}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.divider()
    st.subheader("Getting started")
    st.markdown("""
**1.** Go to **Portfolio** → deposit funds (e.g. `10 000 USDT`) before placing orders.

**2.** Click **Connect** in the sidebar, then choose a data type + symbol and click **Subscribe** to receive live prices.

**3.** Go to **Market Data** to see live prices, trades, and charts.

**4.** Go to **Orders** to place or cancel orders. Fills appear instantly via WebSocket.
    """)
else:
    tab_login, tab_reg = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u and p:
                    data, err = login(u, p)
                    if err:
                        st.error(err)
                    else:
                        set_auth(data["access_token"], u)
                        st.success("Logged in.")
                        st.rerun()
                else:
                    st.warning("Fill in both fields.")

    with tab_reg:
        with st.form("register"):
            u2 = st.text_input("Username", key="ru")
            p2 = st.text_input("Password", type="password", key="rp")
            if st.form_submit_button("Register"):
                if u2 and p2:
                    data, err = register(u2, p2)
                    if err:
                        st.error(err)
                    else:
                        st.success("Account created. Login above.")
                else:
                    st.warning("Fill in both fields.")

st.divider()

# ── Diagnostics (collapsed) ────────────────────────────────────────────────────
with st.expander("System diagnostics"):
    info, err = get_info()
    if err:
        st.error(err)
    elif info:
        c1, c2, c3 = st.columns(3)
        c1.metric("Symbols", len(info.get("trading_pairs", [])))
        c2.metric("Exchanges", len(info.get("exchanges", [])))
        c3.metric("Version", info.get("version", "—"))
        st.caption("Symbols: " + ", ".join(info.get("trading_pairs", [])))
        st.caption("Exchanges: " + ", ".join(info.get("exchanges", [])))

    st.markdown("---")
    # Quick health checks
    def _row(label, ok, detail=""):
        badge = f'<span class="badge badge-{"green" if ok else "red"}">{"PASS" if ok else "FAIL"}</span>'
        detail_html = f' <span style="color:#8b949e;font-size:0.82rem">{detail}</span>' if detail else ""
        st.markdown(f'{badge} {label}{detail_html}', unsafe_allow_html=True)

    _row("Health check", backend_ok)
    _row("GET /info", info is not None)
    ws_ok = client.connected
    _row("WebSocket connection", ws_ok, "" if ws_ok else "Click Connect in the sidebar")

with st.expander("API reference"):
    st.markdown("""
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/info` | No | Server info |
| POST | `/auth/register` | No | Create account |
| POST | `/auth/login` | No | Login → JWT |
| GET | `/balance` | Yes | Account balances |
| POST | `/deposit` | Yes | Deposit asset |
| POST | `/orders` | Yes | Place order |
| GET | `/orders/{token_id}` | Yes | Get order |
| DELETE | `/orders/{token_id}` | Yes | Cancel order |

**WebSocket** `ws://localhost:8000/ws?token=<JWT>`
```json
{"action":"subscribe","data_type":"best_touch","symbol":"BTCUSDT","exchange":"all"}
```
Message types: `best_touch` · `trade` · `kline` · `ewma` · `order_update`
    """)

# ── WS message log (collapsed) ─────────────────────────────────────────────────
with st.expander(f"WebSocket log  ({len(store.log)} messages)"):
    c1, c2 = st.columns(2)
    c1.metric("Total received", len(store.log))
    c2.metric("New this cycle", len(new_msgs))
    if is_authenticated():
        with st.container():
            raw = st.text_area(
                "Send raw JSON",
                value='{"action":"subscribe","data_type":"best_touch","symbol":"BTCUSDT","exchange":"all"}',
                height=80,
            )
            if st.button("Send"):
                try:
                    client.send_raw(json.loads(raw))
                    st.success("Sent.")
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {e}")
    ws_message_log(store.log, max_lines=100)

time.sleep(refresh)
st.rerun()

