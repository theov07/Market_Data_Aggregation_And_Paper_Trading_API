import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import streamlit as st
from utils.theme import page_setup, inject_css
from utils.state import init, is_authenticated
from utils.config import SYMBOLS, EXCHANGES, KLINE_INTERVALS, DATA_TYPES
from services.ws_client import get_client, reset_client
from components.charts import line_chart, candlestick_chart
from components.tables import best_touch_table, trades_table

page_setup("Market Data")
inject_css()
init()

st.title("Market Data")

if "market_store" not in st.session_state:
    from services.data_adapter import MarketDataStore
    st.session_state["market_store"] = MarketDataStore()
store = st.session_state["market_store"]

client = get_client()

# ── Sidebar controls ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Connection")
    token = st.session_state.get("token") if is_authenticated() else None
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Connect", width="stretch", disabled=client.connected):
            client.connect(token)
            st.rerun()
    with col_b:
        if st.button("Disconnect", width="stretch", disabled=not client.connected):
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
    symbol   = st.selectbox("Symbol",    SYMBOLS)
    # best_touch is always broadcast as aggregated ("all"); pre-select it
    # key=f"exc_{dtype}" forces widget recreation (and correct default) on dtype change
    exc_default = EXCHANGES.index("all") if dtype == "best_touch" else 0
    exchange = st.selectbox("Exchange", EXCHANGES, index=exc_default, key=f"exc_{dtype}")
    interval = None
    half_life = None
    if dtype == "kline":
        interval = st.selectbox("Interval", KLINE_INTERVALS)
    if dtype == "ewma":
        half_life = st.number_input("Half-life (s)", value=10.0, min_value=1.0)

    if st.button("Subscribe", width="stretch"):
        if not client.connected:
            client.connect(token)
            time.sleep(1.2)
        client.subscribe(dtype, symbol, exchange, interval, half_life)
        st.rerun()

    st.markdown("---")
    refresh = st.slider("Auto-refresh (s)", 1, 10, 2)

# ── Drain messages into store ──────────────────────────────────────────────────
new_msgs = client.drain()
for msg in new_msgs:
    store.process_message(msg)

# status bar
if not client.connected:
    st.warning("WebSocket not connected. Click Connect in the sidebar first.")
else:
    total = len(store.log)
    st.caption(f"Messages received: {total} | New this cycle: {len(new_msgs)}")
    if total > 0:
        last = store.log[-1]
        st.caption(f"Last: type={last.get('type','?')}  symbol={last.get('data',{}).get('symbol','?')}")

# ── Tabs ───────────────────────────────────────────────────────────────────────
# All tabs use the symbol/exchange already chosen in the sidebar — no duplicate pickers.
tab_bt, tab_trades, tab_kline, tab_ewma = st.tabs(
    ["Best Touch", "Trades", "Klines", "EWMA"]
)

with tab_bt:
    # Filter best_touch by sidebar exchange:
    # "all" shows the cross-exchange aggregated row per symbol
    # "binance"/"okx" shows only that exchange's best bid+ask
    filtered_bt: dict = {}
    for sym_key, exc_dict in store.best_touch.items():
        if exchange in exc_dict:
            filtered_bt[sym_key] = {exchange: exc_dict[exchange]}
        elif exchange == "all" and "all" in exc_dict:
            filtered_bt[sym_key] = {"all": exc_dict["all"]}
    best_touch_table(filtered_bt)

with tab_trades:
    flat: list = []
    for sym_key, t_list in store.trades.items():
        if symbol != "all" and sym_key != symbol:
            continue
        flat.extend(t_list)
    if exchange != "all":
        flat = [t for t in flat if t.exchange == exchange]
    trades_table(flat)

with tab_kline:
    kline_int = interval or st.selectbox("Interval", KLINE_INTERVALS, key="kl_int")
    klines = (
        store.klines
        .get(symbol, {})
        .get(exchange if exchange != "all" else "binance", {})
        .get(kline_int, [])
    )
    if len(klines) >= 2:
        import pandas as pd
        df = pd.DataFrame([
            {
                "open_time": k.open_time, "open": k.open, "high": k.high,
                "low": k.low, "close": k.close, "volume": k.volume,
            }
            for k in klines
        ])
        # Convert Unix epoch float → UTC datetime so x-axis shows readable time
        df["open_time"] = pd.to_datetime(df["open_time"], unit="s", utc=True)
        st.plotly_chart(candlestick_chart(df, f"{symbol} {exchange} {kline_int}"),
                        width="stretch")
    else:
        st.info("Not enough kline data yet. Subscribe to kline in the sidebar and wait for ticks.")

with tab_ewma:
    exc_for_ewma = exchange if exchange != "all" else "binance"
    sym_ewma = store.ewma.get(symbol, {}).get(exc_for_ewma, {})
    if sym_ewma:
        for hl, snap in sym_ewma.items():
            st.markdown(
                f'<div class="kpi-card">'
                f'<div class="kpi-label">EWMA half-life {hl}s — {symbol} {exc_for_ewma}</div>'
                f'<div class="kpi-value">{snap.value:,.4f}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No EWMA data. Subscribe to ewma in the sidebar.")

time.sleep(refresh)
st.rerun()
