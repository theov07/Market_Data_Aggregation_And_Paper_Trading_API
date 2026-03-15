"""
Reusable metric card components rendered as HTML.
CSS classes are defined in utils/theme.py.
"""
import streamlit as st


def metric_card(title: str, value: str, delta: str = "", delta_positive: bool | None = None):
    """Render a styled KPI card."""
    if delta:
        color = "#22c55e" if delta_positive else "#ef4444" if delta_positive is False else "#94a3b8"
        delta_html = f'<div class="kpi-delta" style="color:{color}">{delta}</div>'
    else:
        delta_html = ""

    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{title}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{delta_html}</div>',
        unsafe_allow_html=True,
    )


def connection_card(connected: bool, label: str = "Backend"):
    color = "#22c55e" if connected else "#ef4444"
    status = "Online" if connected else "Offline"
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="color:{color}">{status}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
