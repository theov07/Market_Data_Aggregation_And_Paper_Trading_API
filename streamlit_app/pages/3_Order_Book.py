import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import streamlit as st
from utils.theme import page_setup, inject_css
from utils.state import init, is_authenticated
from utils.config import SYMBOLS, EXCHANGES
from services.ws_client import get_client
from components.charts import line_chart

page_setup("Order Book")
inject_css()
init()

st.title("Order Book — Best Touch")

if "market_store" not in st.session_state:
    from services.data_adapter import MarketDataStore
    st.session_state["market_store"] = MarketDataStore()
store = st.session_state["market_store"]

client = get_client()

with st.sidebar:
    st.markdown("### Subscribe")
    token = st.session_state.get("token") if is_authenticated() else None
    sym = st.selectbox("Symbol", SYMBOLS)
    exc = st.selectbox("Exchange", EXCHANGES)

    if st.button("Subscribe best_touch"):
        if not client.connected:
            client.connect(token)
            time.sleep(1.2)
        client.subscribe("best_touch", sym, exc)
        st.success("Subscribed.")

    st.markdown("---")
    refresh = st.slider("Auto-refresh (s)", 1, 10, 3)

for msg in client.drain():
    store.process_message(msg)

# ── Best touch grid ────────────────────────────────────────────────────────────
bt = store.best_touch
if not bt:
    st.info("No order book data. Subscribe to best_touch data.")
    time.sleep(refresh)
    st.rerun()

for symbol, exchanges in bt.items():
    # Only show the exchange(s) matching the sidebar selection
    display = {k: v for k, v in exchanges.items() if exc == "all" or k == exc}
    if not display:
        continue
    st.subheader(symbol)
    cols = st.columns(len(display))
    for col, (exc_name, snap) in zip(cols, display.items()):
        spread_pct = snap.spread / snap.mid * 100 if snap.mid else 0
        col.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">{exc_name}</div>'
            f'<div style="display:flex;gap:24px;margin-top:4px">'
            f'  <div><div class="kpi-label">Bid</div>'
            f'       <div class="kpi-value" style="color:#3fb950">{snap.best_bid_price:,.2f}</div>'
            f'       <div class="kpi-sub">{snap.bid_exchange}</div></div>'
            f'  <div><div class="kpi-label">Ask</div>'
            f'       <div class="kpi-value" style="color:#f85149">{snap.best_ask_price:,.2f}</div>'
            f'       <div class="kpi-sub">{snap.ask_exchange}</div></div>'
            f'  <div><div class="kpi-label">Spread</div>'
            f'       <div class="kpi-value" style="font-size:1rem">{snap.spread:.4f}</div>'
            f'       <div class="kpi-sub">{spread_pct:.4f}%</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

time.sleep(refresh)
st.rerun()
