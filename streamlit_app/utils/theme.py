"""
Theme helpers — minimal professional dark style.
"""
import streamlit as st


CUSTOM_CSS = """
<style>
[data-testid="stAppViewContainer"] { background: #f6f8fb; }
[data-testid="stSidebar"]          { background: #ffffff; border-right: 1px solid #e5e7eb; }
[data-testid="stSidebar"] * { font-size: 0.875rem; }
div[data-testid="metric-container"] { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 12px 16px; }
h1 { font-size: 1.4rem !important; font-weight: 600; color: #111827; }
h2 { font-size: 1.1rem !important; font-weight: 600; color: #1f2937; margin-top: 1.2rem; }
h3 { font-size: 0.95rem !important; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 6px;
            padding: 14px 18px; margin-bottom: 4px; }
.kpi-label { font-size: 0.72rem; color: #6b7280; text-transform: uppercase;
              letter-spacing: 0.06em; margin-bottom: 2px; }
.kpi-value { font-size: 1.45rem; font-weight: 700; color: #111827; }
.kpi-sub   { font-size: 0.78rem; color: #6b7280; margin-top: 2px; }
.status-ok  { color: #3fb950; font-weight: 600; }
.status-err { color: #f85149; font-weight: 600; }
.badge { display: inline-block; padding: 1px 7px; border-radius: 3px;
         font-size: 0.72rem; font-weight: 600; letter-spacing: 0.03em; }
.badge-green  { background: #ecfdf3; color: #15803d; border: 1px solid #bbf7d0; }
.badge-red    { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.badge-blue   { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.badge-orange { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
.badge-gray   { background: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }
.ws-log { height: 360px; overflow-y: auto; background: #ffffff;
          border: 1px solid #e5e7eb; border-radius: 6px;
          padding: 10px 14px; font-family: "SFMono-Regular", Consolas, monospace;
          font-size: 0.76rem; color: #374151; line-height: 1.5; }
div[data-testid="stHorizontalBlock"] { gap: 10px; }
.stTabs [data-baseweb="tab"] { font-size: 0.82rem; }
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def page_setup(title: str):
    st.set_page_config(page_title=title, page_icon=None, layout="wide")
    inject_css()
