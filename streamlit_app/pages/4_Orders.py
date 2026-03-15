import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
import streamlit as st
from utils.theme import page_setup, inject_css
from utils.state import init, is_authenticated, upsert_order
from utils.config import SYMBOLS
from services.api_client import create_order, cancel_order, modify_order, get_order
from components.tables import orders_table
from components.status import auth_required

page_setup("Orders")
inject_css()
init()

st.title("Orders")
auth_required(is_authenticated())

token = st.session_state["token"]
orders = st.session_state.get("orders", [])

tab_place, tab_manage = st.tabs(["Place Order", "Manage Orders"])

# ── Place order ────────────────────────────────────────────────────────────────
with tab_place:
    with st.form("place_order"):
        c1, c2 = st.columns(2)
        with c1:
            sym       = st.selectbox("Symbol", SYMBOLS)
            side      = st.selectbox("Side", ["buy", "sell"])
            order_type = st.selectbox("Type", ["market", "limit"])
        with c2:
            qty   = st.number_input("Quantity", min_value=0.0001, step=0.001, format="%.4f")
            price = st.number_input("Price (limit only)", min_value=0.0, step=0.01, format="%.2f")
            tid   = st.text_input("Token ID (optional — auto-generated if blank)")

        submitted = st.form_submit_button("Submit order", width="stretch")

    if submitted:
        final_tid = tid.strip() or str(uuid.uuid4())[:8]
        final_price = price if order_type == "limit" else None
        data, err = create_order(token, final_tid, sym, side, order_type, qty, final_price)
        if err:
            st.error(err)
        else:
            upsert_order(data)
            st.success(f"Order submitted: {final_tid}")
            st.json(data)

# ── Manage orders ──────────────────────────────────────────────────────────────
with tab_manage:
    if not orders:
        st.info("No orders in session. Place an order first.")
    else:
        orders_table(orders)
        st.divider()

        col_cancel, col_modify = st.columns(2)

        with col_cancel:
            st.subheader("Cancel")
            tids = [o["token_id"] for o in orders if o.get("status") == "open"]
            if tids:
                to_cancel = st.selectbox("Order to cancel", tids, key="cancel_sel")
                if st.button("Cancel order"):
                    data, err = cancel_order(token, to_cancel)
                    if err:
                        st.error(err)
                    else:
                        upsert_order(data)
                        st.success("Order cancelled.")
                        st.rerun()
            else:
                st.caption("No open orders.")

        with col_modify:
            st.subheader("Modify")
            tids_mod = [o["token_id"] for o in orders if o.get("status") == "open"]
            if tids_mod:
                to_mod = st.selectbox("Order to modify", tids_mod, key="mod_sel")
                new_price = st.number_input("New price", min_value=0.0, step=0.01, format="%.2f", key="mod_p")
                new_qty   = st.number_input("New quantity", min_value=0.0001, step=0.001, format="%.4f", key="mod_q")
                if st.button("Apply modification"):
                    data, err = modify_order(
                        token, to_mod,
                        price=new_price if new_price > 0 else None,
                        quantity=new_qty if new_qty > 0 else None,
                    )
                    if err:
                        st.error(err)
                    else:
                        upsert_order(data)
                        st.success("Order modified.")
                        st.rerun()
            else:
                st.caption("No open orders.")

    st.divider()
    st.subheader("Refresh from API")
    fetch_tid = st.text_input("Token ID to refresh")
    if st.button("Fetch"):
        if fetch_tid:
            data, err = get_order(token, fetch_tid)
            if err:
                st.error(err)
            else:
                upsert_order(data)
                st.json(data)
