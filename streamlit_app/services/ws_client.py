"""
Thread-backed WebSocket client for Streamlit.
Compatible with websockets >= 10.

Usage
-----
    from services.ws_client import get_client, reset_client

    client = get_client()
    client.connect(token)               # optional JWT
    client.subscribe("best_touch", "BTCUSDT", "binance")
    client.send_raw({"action": ...})
    msgs = client.drain()               # list[dict] since last call
    client.disconnect()
"""
import asyncio
import json
import threading
import time
from typing import Optional

import websockets
import websockets.legacy.client

from .config import WS_BASE


class WSClient:
    """Persistent async WebSocket client running in a background thread."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws = None
        self._running = False
        self._token: Optional[str] = None

        self._send_queue: list[str] = []
        self._send_lock  = threading.Lock()
        self._recv_buf:  list[dict] = []
        self._recv_lock  = threading.Lock()

        self.connected = False
        self.error:    Optional[str] = None

    # ---- public API ----------------------------------------------------------

    def connect(self, token: Optional[str] = None):
        if self._running:
            return
        self._token   = token
        self._running = True
        self._thread  = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        # give the background loop ~1.5 s to establish the connection
        time.sleep(1.5)

    def disconnect(self):
        self._running = False
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._close(), self._loop)
        self.connected = False

    def send_raw(self, payload: dict):
        with self._send_lock:
            self._send_queue.append(json.dumps(payload))

    def subscribe(
        self, data_type: str, symbol: str,
        exchange: str = "all",
        interval: Optional[str] = None,
        half_life: Optional[float] = None,
    ):
        msg: dict = {"action": "subscribe", "data_type": data_type,
                     "symbol": symbol, "exchange": exchange}
        if interval:
            msg["interval"] = interval
        if half_life is not None:
            msg["half_life"] = half_life
        self.send_raw(msg)

    def unsubscribe(self, data_type: str, symbol: str,
                    exchange: str = "all", interval: Optional[str] = None):
        msg: dict = {"action": "unsubscribe", "data_type": data_type,
                     "symbol": symbol, "exchange": exchange}
        if interval:
            msg["interval"] = interval
        self.send_raw(msg)

    def drain(self) -> list[dict]:
        with self._recv_lock:
            msgs = list(self._recv_buf)
            self._recv_buf.clear()
        return msgs

    def peek(self) -> list[dict]:
        with self._recv_lock:
            return list(self._recv_buf)

    # ---- background loop ----------------------------------------------------

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._main())

    async def _main(self):
        url = WS_BASE if not self._token else f"{WS_BASE}?token={self._token}"
        try:
            async with websockets.legacy.client.connect(
                url, ping_interval=20, ping_timeout=30
            ) as ws:
                self._ws       = ws
                self.connected = True
                self.error     = None

                recv_task = asyncio.create_task(self._recv_loop(ws))
                send_task = asyncio.create_task(self._send_loop(ws))

                done, pending = await asyncio.wait(
                    {recv_task, send_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pending:
                    t.cancel()
        except Exception as exc:
            self.error = str(exc)
        finally:
            self.connected = False
            self._running  = False

    async def _recv_loop(self, ws):
        while self._running:
            try:
                raw  = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(raw)
                with self._recv_lock:
                    self._recv_buf.append(data)
                    if len(self._recv_buf) > 2000:
                        self._recv_buf = self._recv_buf[-2000:]
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    async def _send_loop(self, ws):
        while self._running:
            with self._send_lock:
                pending = list(self._send_queue)
                self._send_queue.clear()
            for msg in pending:
                try:
                    await ws.send(msg)
                except Exception:
                    pass
            await asyncio.sleep(0.05)

    async def _close(self):
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass


# ---- singleton -----------------------------------------------------------

_instance: Optional[WSClient] = None
_lock = threading.Lock()


def get_client() -> WSClient:
    global _instance
    with _lock:
        if _instance is None:
            _instance = WSClient()
    return _instance


def reset_client() -> WSClient:
    global _instance
    with _lock:
        if _instance is not None:
            _instance.disconnect()
        _instance = WSClient()
    return _instance

import asyncio
import json
import threading
import time
from typing import Optional

import websockets

from .config import WS_BASE   # type: ignore[import]


class WSClient:
    """Persistent async WebSocket client running in a background thread."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws = None
        self._running = False
        self._token: Optional[str] = None

        # Thread-safe queue for outgoing messages
        self._send_queue: list[str] = []
        self._send_lock = threading.Lock()

        # Received messages buffer
        self._recv_buffer: list[dict] = []
        self._recv_lock = threading.Lock()

        self.connected = False
        self.error: Optional[str] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def connect(self, token: Optional[str] = None):
        if self._running:
            return
        self._token = token
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        # Give background thread ~1 s to establish connection
        time.sleep(1.0)

    def disconnect(self):
        self._running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._close(), self._loop)
        self.connected = False

    def send_raw(self, payload: dict):
        with self._send_lock:
            self._send_queue.append(json.dumps(payload))

    def subscribe(
        self,
        data_type: str,
        symbol: str,
        exchange: str = "all",
        interval: Optional[str] = None,
        half_life: Optional[float] = None,
    ):
        msg: dict = {
            "action":    "subscribe",
            "data_type": data_type,
            "symbol":    symbol,
            "exchange":  exchange,
        }
        if interval:
            msg["interval"] = interval
        if half_life is not None:
            msg["half_life"] = half_life
        self.send_raw(msg)

    def unsubscribe(
        self,
        data_type: str,
        symbol: str,
        exchange: str = "all",
        interval: Optional[str] = None,
    ):
        msg: dict = {
            "action":    "unsubscribe",
            "data_type": data_type,
            "symbol":    symbol,
            "exchange":  exchange,
        }
        if interval:
            msg["interval"] = interval
        self.send_raw(msg)

    def drain(self) -> list[dict]:
        """Return all buffered messages and clear the buffer."""
        with self._recv_lock:
            msgs = list(self._recv_buffer)
            self._recv_buffer.clear()
        return msgs

    def peek(self) -> list[dict]:
        """Return a copy of buffered messages without clearing."""
        with self._recv_lock:
            return list(self._recv_buffer)

    # ── Background async loop ─────────────────────────────────────────────────

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._main())

    async def _main(self):
        url = WS_BASE
        if self._token:
            url = f"{WS_BASE}?token={self._token}"
        try:
            async with websockets.connect(url, ping_interval=20) as ws:  # type: ignore[attr-defined]
                self._ws = ws
                self.connected = True
                self.error = None
                recv_task = asyncio.create_task(self._recv_loop(ws))
                send_task = asyncio.create_task(self._send_loop(ws))
                done, pending = await asyncio.wait(
                    [recv_task, send_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pending:
                    t.cancel()
        except Exception as e:
            self.error = str(e)
        finally:
            self.connected = False
            self._running = False

    async def _recv_loop(self, ws):
        while self._running:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {"raw": raw}
                with self._recv_lock:
                    self._recv_buffer.append(data)
                    if len(self._recv_buffer) > 2000:
                        self._recv_buffer = self._recv_buffer[-2000:]
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    async def _send_loop(self, ws):
        while self._running:
            with self._send_lock:
                pending = list(self._send_queue)
                self._send_queue.clear()
            for msg in pending:
                try:
                    await ws.send(msg)
                except Exception:
                    pass
            await asyncio.sleep(0.05)

    async def _close(self):
        if self._ws:
            await self._ws.close()


# ── Singleton helper ──────────────────────────────────────────────────────────

_instance: Optional[WSClient] = None
_lock = threading.Lock()


def get_client() -> WSClient:
    global _instance
    with _lock:
        if _instance is None:
            _instance = WSClient()
    return _instance


def reset_client():
    global _instance
    with _lock:
        if _instance is not None:
            _instance.disconnect()
        _instance = WSClient()
    return _instance
