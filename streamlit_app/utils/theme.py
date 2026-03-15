"""
Theme helpers — minimal professional dark style.
"""
import streamlit as st


CUSTOM_CSS = """
<style>
[data-testid="stAppViewContainer"] { background: #0d1117; }
[data-testid="stSidebar"]          { background: #161b22; border-right: 1px solid #21262d; }
[data-testid="stSidebar"] * { font-size: 0.875rem; }
div[data-testid="metric-container"] { background: #161b22; border: 1px solid #21262d; border-radius: 6px; padding: 12px 16px; }
h1 { font-size: 1.4rem !important; font-weight: 600; color: #e6edf3; }
h2 { font-size: 1.1rem !important; font-weight: 600; color: #c9d1d9; margin-top: 1.2rem; }
h3 { font-size: 0.95rem !important; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-card { background: #161b22; border: 1px solid #21262d; border-radius: 6px;
            padding: 14px 18px; margin-bottom: 4px; }
.kpi-label { font-size: 0.72rem; color: #8b949e; text-transform: uppercase;
              letter-spacing: 0.06em; margin-bottom: 2px; }
.kpi-value { font-size: 1.45rem; font-weight: 700; color: #e6edf3; }
.kpi-sub   { font-size: 0.78rem; color: #6e7681; margin-top: 2px; }
.status-ok  { color: #3fb950; font-weight: 600; }
.status-err { color: #f85149; font-weight: 600; }
.badge { display: inline-block; padding: 1px 7px; border-radius: 3px;
         font-size: 0.72rem; font-weight: 600; letter-spacing: 0.03em; }
.badge-green  { background: #0f2a1a; color: #3fb950; border: 1px solid #1e4427; }
.badge-red    { background: #2a0f0f; color: #f85149; border: 1px solid #421e1e; }
.badge-blue   { background: #0f1f2a; color: #58a6ff; border: 1px solid #1e3a5f; }
.badge-orange { background: #2a1a0f; color: #d29922; border: 1px solid #4a3010; }
.badge-gray   { background: #1c2128; color: #8b949e; border: 1px solid #2d333b; }
.ws-log { height: 360px; overflow-y: auto; background: #0d1117;
          border: 1px solid #21262d; border-radius: 6px;
          padding: 10px 14px; font-family: "SFMono-Regular", Consolas, monospace;
          font-size: 0.76rem; color: #8b949e; line-height: 1.5; }
div[data-testid="stHorizontalBlock"] { gap: 10px; }
.stTabs [data-baseweb="tab"] { font-size: 0.82rem; }
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def page_setup(title: str):
    st.set_page_config(page_title=title, page_icon=None, layout="wide")
    inject_css()
