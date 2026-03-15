"""
Reusable status / alert widgets.
"""
import json
import streamlit as st


def auth_required(is_authenticated: bool):
    """Stop page rendering if user is not authenticated."""
    if not is_authenticated:
        st.warning("Please log in first via the Home page.")
        st.stop()


def backend_offline_banner(error: str | None = None):
    msg = error or "Backend is offline — start the server with `python run_server.py`."
    st.error(msg)


def ws_message_log(messages: list[dict], max_lines: int = 200):
    """Render the last N WS messages in a scrollable code block."""
    if not messages:
        st.info("No messages received yet.")
        return
    displayed = messages[-max_lines:]
    lines = [json.dumps(m, default=str) for m in reversed(displayed)]
    st.markdown(
        f'<div class="ws-log">{"<br>".join(lines)}</div>',
        unsafe_allow_html=True,
    )
