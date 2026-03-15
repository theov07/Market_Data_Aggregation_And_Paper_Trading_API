"""
REST API client for the paper-trading backend.

All methods return (data, error_str). Error is None on success.
"""
import requests
from typing import Any, Optional, Tuple

from .config import API_BASE

_TIMEOUT = 8   # seconds


def _headers(token: Optional[str]) -> dict:
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


# ── Auth ──────────────────────────────────────────────────────────────────────

def register(username: str, password: str) -> Tuple[Optional[dict], Optional[str]]:
    try:
        r = requests.post(
            f"{API_BASE}/auth/register",
            json={"username": username, "password": password},
            timeout=_TIMEOUT,
        )
        if r.ok:
            return r.json(), None
        return None, r.json().get("detail", r.text)
    except requests.ConnectionError:
        return None, "Cannot reach backend — is it running?"
    except Exception as e:
        return None, str(e)


def login(username: str, password: str) -> Tuple[Optional[dict], Optional[str]]:
    try:
        r = requests.post(
            f"{API_BASE}/auth/login",
            json={"username": username, "password": password},
            timeout=_TIMEOUT,
        )
        if r.ok:
            return r.json(), None
        return None, r.json().get("detail", r.text)
    except requests.ConnectionError:
        return None, "Cannot reach backend — is it running?"
    except Exception as e:
        return None, str(e)


# ── Info ──────────────────────────────────────────────────────────────────────

def get_info() -> Tuple[Optional[dict], Optional[str]]:
    try:
        r = requests.get(f"{API_BASE}/info", timeout=_TIMEOUT)
        if r.ok:
            return r.json(), None
        return None, r.text
    except requests.ConnectionError:
        return None, "Cannot reach backend"
    except Exception as e:
        return None, str(e)


def health_check() -> bool:
    try:
        r = requests.get(f"{API_BASE}/info", timeout=3)
        return r.ok
    except Exception:
        return False


# ── Trading ───────────────────────────────────────────────────────────────────

def get_balance(token: str) -> Tuple[Optional[dict], Optional[str]]:
    try:
        r = requests.get(
            f"{API_BASE}/balance",
            headers=_headers(token),
            timeout=_TIMEOUT,
        )
        if r.ok:
            return r.json(), None
        return None, r.json().get("detail", r.text)
    except requests.ConnectionError:
        return None, "Cannot reach backend"
    except Exception as e:
        return None, str(e)


def deposit(token: str, asset: str, amount: float) -> Tuple[Optional[dict], Optional[str]]:
    try:
        r = requests.post(
            f"{API_BASE}/deposit",
            json={"asset": asset, "amount": amount},
            headers=_headers(token),
            timeout=_TIMEOUT,
        )
        if r.ok:
            return r.json(), None
        return None, r.json().get("detail", r.text)
    except requests.ConnectionError:
        return None, "Cannot reach backend"
    except Exception as e:
        return None, str(e)


def create_order(
    token: str,
    token_id: str,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
) -> Tuple[Optional[dict], Optional[str]]:
    payload: dict[str, Any] = {
        "token_id":   token_id,
        "symbol":     symbol,
        "side":       side,
        "order_type": order_type,
        "quantity":   quantity,
    }
    if price is not None:
        payload["price"] = price
    try:
        r = requests.post(
            f"{API_BASE}/orders",
            json=payload,
            headers=_headers(token),
            timeout=_TIMEOUT,
        )
        if r.ok:
            return r.json(), None
        return None, r.json().get("detail", r.text)
    except requests.ConnectionError:
        return None, "Cannot reach backend"
    except Exception as e:
        return None, str(e)


def get_order(token: str, token_id: str) -> Tuple[Optional[dict], Optional[str]]:
    try:
        r = requests.get(
            f"{API_BASE}/orders/{token_id}",
            headers=_headers(token),
            timeout=_TIMEOUT,
        )
        if r.ok:
            return r.json(), None
        return None, r.json().get("detail", r.text)
    except requests.ConnectionError:
        return None, "Cannot reach backend"
    except Exception as e:
        return None, str(e)


def cancel_order(token: str, token_id: str) -> Tuple[Optional[dict], Optional[str]]:
    try:
        r = requests.delete(
            f"{API_BASE}/orders/{token_id}",
            headers=_headers(token),
            timeout=_TIMEOUT,
        )
        if r.ok:
            return r.json(), None
        return None, r.json().get("detail", r.text)
    except requests.ConnectionError:
        return None, "Cannot reach backend"
    except Exception as e:
        return None, str(e)


def modify_order(
    token: str,
    token_id: str,
    price: Optional[float] = None,
    quantity: Optional[float] = None,
) -> Tuple[Optional[dict], Optional[str]]:
    payload: dict[str, Any] = {}
    if price is not None:
        payload["price"] = price
    if quantity is not None:
        payload["quantity"] = quantity
    try:
        r = requests.put(
            f"{API_BASE}/orders/{token_id}",
            json=payload,
            headers=_headers(token),
            timeout=_TIMEOUT,
        )
        if r.ok:
            return r.json(), None
        return None, r.json().get("detail", r.text)
    except requests.ConnectionError:
        return None, "Cannot reach backend"
    except Exception as e:
        return None, str(e)
