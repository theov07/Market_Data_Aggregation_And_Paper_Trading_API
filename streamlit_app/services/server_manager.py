"""
Manages the FastAPI backend process so it can be started/stopped
from the Streamlit UI without needing a separate terminal.

The process handle is stored at module level so it is shared across
all Streamlit sessions in the same Python process.
"""

import os
import re
import signal
import sys
import secrets
import subprocess
import threading
import time

# ── Paths ──────────────────────────────────────────────────────────────────────
# streamlit_app/services/ → up two levels → project root
_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
_SECRET_KEY_FILE = os.path.join(PROJECT_ROOT, ".secret_key")

# Use the exact Python interpreter that is running Streamlit (respects venv)
_PYTHON = sys.executable

# ── Module-level state (shared across all sessions) ────────────────────────────
_process: "subprocess.Popen | None" = None
_lock = threading.Lock()
_auto_stop_timer: "threading.Timer | None" = None

AUTO_STOP_SECONDS = 10 * 60  # 10 minutes


# ── Secret key ─────────────────────────────────────────────────────────────────

def _get_secret_key() -> str:
    """Return a persistent SECRET_KEY, generating one if needed."""
    # 1. Honour existing environment variable (e.g. set by Streamlit Cloud secrets)
    env_key = os.environ.get("SECRET_KEY", "")
    if len(env_key) >= 32:
        return env_key

    # 2. Load from file if available
    if os.path.exists(_SECRET_KEY_FILE):
        with open(_SECRET_KEY_FILE) as f:
            key = f.read().strip()
        if len(key) >= 32:
            return key

    # 3. Generate, persist and return a new key
    key = secrets.token_hex(32)
    try:
        with open(_SECRET_KEY_FILE, "w") as f:
            f.write(key)
    except OSError:
        pass  # read-only filesystem (e.g. Streamlit Cloud) — key lives in memory
    return key


# ── Port helpers ───────────────────────────────────────────────────────────────

def _pids_on_port(port: int) -> list[int]:
    """Return all PIDs listening on *port* (macOS/Linux)."""
    # Try lsof first (macOS and some Linux distros)
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f"tcp:{port}"],
            stderr=subprocess.DEVNULL,
        ).decode()
        return [int(p) for p in out.split() if p.strip().isdigit()]
    except subprocess.CalledProcessError:
        return []  # lsof exits 1 when nothing is listening
    except FileNotFoundError:
        pass  # lsof not installed; fall through to ss

    # Fallback: ss (available on Linux)
    try:
        out = subprocess.check_output(
            ["ss", "-Htlnp", f"sport = :{port}"],
            stderr=subprocess.DEVNULL,
        ).decode()
        return [int(m) for m in re.findall(r"pid=(\d+)", out)]
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []


def _free_port(port: int) -> None:
    """Kill every process currently bound to *port*, then wait until it's free."""
    pids = _pids_on_port(port)
    for pid in pids:
        try:
            # Try graceful first, then SIGKILL
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    if pids:
        time.sleep(0.8)  # give them a moment to exit cleanly

    # If any are still alive, force-kill
    for pid in _pids_on_port(port):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    # Wait until the port is actually free (up to 3 s)
    for _ in range(30):
        if not _pids_on_port(port):
            break
        time.sleep(0.1)


# ── Process control ────────────────────────────────────────────────────────────

def is_running() -> bool:
    """Return True if the server process is alive."""
    return _process is not None and _process.poll() is None


def get_pid() -> "int | None":
    return _process.pid if _process is not None else None


def start_server(wait_seconds: float = 3.0) -> tuple[bool, str]:
    """
    Start the FastAPI backend.
    Returns (success: bool, message: str).
    After AUTO_STOP_SECONDS the server is stopped automatically.
    """
    global _process, _auto_stop_timer
    with _lock:
        if is_running():
            return True, "Server already running"

        # Cancel any pending auto-stop from a previous run
        if _auto_stop_timer is not None:
            _auto_stop_timer.cancel()
            _auto_stop_timer = None

        # Kill anything already bound to the API port before we start
        try:
            from config import API_PORT as _port
        except Exception:
            _port = 8000
        _free_port(_port)

        secret_key = _get_secret_key()
        env = os.environ.copy()
        env["SECRET_KEY"] = secret_key

        try:
            _process = subprocess.Popen(
                [_PYTHON, "run_server.py"],
                cwd=PROJECT_ROOT,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,  # capture stderr to surface startup errors
                start_new_session=True,   # isolate process group so we can kill all children
            )
        except Exception as e:
            return False, f"Failed to launch process: {e}"

        # Wait briefly and check the process did not exit immediately
        time.sleep(wait_seconds)
        if _process.poll() is not None:
            try:
                err = _process.stderr.read(500).decode(errors="replace")
            except Exception:
                err = ""
            return False, f"Server exited (code {_process.returncode}). {err}"

        # Schedule automatic shutdown after AUTO_STOP_SECONDS
        _auto_stop_timer = threading.Timer(AUTO_STOP_SECONDS, stop_server)
        _auto_stop_timer.daemon = True
        _auto_stop_timer.start()

        return True, f"Server started (PID {_process.pid})"


def stop_server() -> tuple[bool, str]:
    """Terminate the backend process gracefully."""
    global _process, _auto_stop_timer
    with _lock:
        # Cancel pending auto-stop timer if called manually
        if _auto_stop_timer is not None:
            _auto_stop_timer.cancel()
            _auto_stop_timer = None
        if not is_running():
            _process = None
            return True, "Server not running"
        pid = _process.pid
        try:
            pgid = os.getpgid(pid)
            # Kill the entire process group (handles uvicorn reload workers)
            os.killpg(pgid, signal.SIGTERM)
            try:
                _process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                os.killpg(pgid, signal.SIGKILL)
                _process.wait(timeout=4)
        except ProcessLookupError:
            pass  # already gone
        except Exception as e:
            return False, str(e)
        _process = None
        return True, f"Server stopped (was PID {pid})"


def restart_server() -> tuple[bool, str]:
    stop_server()
    time.sleep(1)
    return start_server()
