import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from utils.theme import page_setup, inject_css
from utils.state import init, is_authenticated
from services.api_client import get_balance, deposit
from components.tables import balances_table
from components.status import auth_required

page_setup("Portfolio")
inject_css()
init()

st.title("Portfolio & Balances")
auth_required(is_authenticated())

token = st.session_state["token"]

# ── Deposit first ─────────────────────────────────────────────────────
st.subheader("1. Deposit") 
st.caption("Add funds before placing orders. Start with at least 1 000 USDT to test limit orders.")
with st.form("deposit"):
    c1, c2 = st.columns(2)
    with c1:
        asset = st.text_input("Asset", value="USDT")
    with c2:
        amount = st.number_input("Amount", min_value=0.0001, value=10000.0, step=1000.0)
    if st.form_submit_button("Deposit", width="stretch"):
        data, err = deposit(token, asset, amount)
        if err:
            st.error(err)
        else:
            st.success(f"Deposited {amount:,.0f} {asset}. Refresh to see updated balances.")
            st.rerun()

st.divider()
st.subheader("2. Current balances")
bal, err = get_balance(token)
if err:
    st.error(err)
else:
    assets = bal.get("balances", [])
    if assets:
        cols = st.columns(min(len(assets), 4))
        for col, a in zip(cols, assets):
            col.markdown(
                f'<div class="kpi-card">'
                f'<div class="kpi-label">{a["asset"]}</div>'
                f'<div class="kpi-value">{a["available"]:,.4f}</div>'
                f'<div class="kpi-sub">reserved {a.get("reserved", 0):,.4f} | total {a["total"]:,.4f}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown("")
        balances_table(assets)
    else:
        st.info("No balances yet. Use the deposit form above.")

st.divider()
st.caption("Next: go to Orders to place a trade.")
