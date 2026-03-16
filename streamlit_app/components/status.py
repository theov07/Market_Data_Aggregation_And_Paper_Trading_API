"""
Reusable status / alert widgets.
"""
import os
import json
import streamlit as st


def auth_required(is_authenticated: bool):
    """Stop page rendering if user is not authenticated."""
    if not is_authenticated:
        st.warning("Please log in first via the Home page.")
        st.stop()


def backend_offline_banner(error: str | None = None):
    start_cmd = (
        '$env:SECRET_KEY = "your-secure-secret-key-min-32-chars"; python run_server.py'
        if os.name == "nt"
        else "SECRET_KEY=$(openssl rand -hex 32) python run_server.py"
    )
    msg = error or f"Backend is offline — start the server with `{start_cmd}`."
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
