import asyncio
import json
import os
import threading
import time

import requests
import websockets

BASE = os.getenv("BASE_URL", "http://localhost:8000")
WS = os.getenv("WS_URL", BASE.replace("http://", "ws://").replace("https://", "wss://") + "/ws")


def assert_ok(response, context: str):
    if response.status_code >= 400:
        raise RuntimeError(f"{context} failed: {response.status_code} {response.text}")


def register_and_seed():
    username = f"ws_thread_{int(time.time())}"
    password = "SecurePass123!"
    reg = requests.post(f"{BASE}/auth/register", json={"username": username, "password": password}, timeout=10)
    assert_ok(reg, "register")
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for asset, amount in (("USDT", 10000.0), ("BTC", 2.0)):
        dep = requests.post(f"{BASE}/deposit", json={"asset": asset, "amount": amount}, headers=headers, timeout=10)
        assert_ok(dep, f"deposit {asset}")

    return username, token, headers


async def ws_listener(token: str, target: dict, ready: threading.Event, stop: threading.Event):
    async with websockets.connect(f"{WS}?token={token}", open_timeout=5, close_timeout=1) as ws:
        welcome = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        target["welcome"] = welcome
        print("WELCOME:", welcome, flush=True)
        ready.set()

        while not stop.is_set():
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            message = json.loads(raw)
            print("WS:", message, flush=True)
            target.setdefault("messages", []).append(message)
            wanted_token = target.get("token_id")
            if message.get("type") == "order_update" and message.get("data", {}).get("token_id") == wanted_token:
                target["order_update"] = message
                return


def listener_thread(token: str, target: dict, ready: threading.Event, stop: threading.Event):
    asyncio.run(ws_listener(token, target, ready, stop))


def main():
    username, token, headers = register_and_seed()
    print("USER:", username, flush=True)

    target: dict = {}
    ready = threading.Event()
    stop = threading.Event()
    thread = threading.Thread(target=listener_thread, args=(token, target, ready, stop), daemon=True)
    thread.start()

    if not ready.wait(timeout=10):
        raise RuntimeError("websocket listener did not become ready")

    token_id = f"thread_fill_{int(time.time() * 1_000_000)}"
    target["token_id"] = token_id

    create = requests.post(
        f"{BASE}/orders",
        json={
            "token_id": token_id,
            "symbol": "BTCUSDT",
            "side": "sell",
            "order_type": "limit",
            "price": 90000.0,
            "quantity": 0.5,
        },
        headers=headers,
        timeout=10,
    )
    assert_ok(create, "create open order")
    print("CREATE:", create.json(), flush=True)

    modify = requests.put(
        f"{BASE}/orders/{token_id}",
        json={"price": 1.0},
        headers=headers,
        timeout=10,
    )
    assert_ok(modify, "modify order")
    print("MODIFY:", modify.json(), flush=True)

    final_order = None
    deadline = time.time() + 12
    while time.time() < deadline:
        order = requests.get(f"{BASE}/orders/{token_id}", headers=headers, timeout=10)
        assert_ok(order, "get order")
        final_order = order.json()
        if final_order["status"] == "filled":
            print("FILLED:", final_order, flush=True)
            break
        time.sleep(0.5)

    thread.join(timeout=5)
    stop.set()

    balances = requests.get(f"{BASE}/balance", headers=headers, timeout=10)
    assert_ok(balances, "get balances")
    negatives = [item for item in balances.json()["balances"] if item["total"] < 0 or item["available"] < 0 or item["reserved"] < 0]
    print("NEGATIVE BALANCES:", negatives, flush=True)
    print("ORDER UPDATE RECEIVED:", target.get("order_update"), flush=True)

    if target.get("order_update") is None:
        raise RuntimeError("order_update not received")
    if final_order is None or final_order["status"] != "filled":
        raise RuntimeError(f"final order not filled: {final_order}")
    if final_order["filled_quantity"] != final_order["quantity"]:
        raise RuntimeError(f"filled_quantity mismatch: {final_order['filled_quantity']} vs {final_order['quantity']}")
    if negatives:
        raise RuntimeError(f"negative balances detected: {negatives}")

    print("SUCCESS", flush=True)


if __name__ == "__main__":
    main()
