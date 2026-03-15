import asyncio
import json
import os
import time
import requests
import websockets

BASE = os.getenv("BASE_URL", "http://localhost:8000")
WS = os.getenv("WS_URL", BASE.replace("http://", "ws://").replace("https://", "wss://") + "/ws")


def assert_ok(response, context: str):
    if response.status_code >= 400:
        raise RuntimeError(f"{context} failed: {response.status_code} {response.text}")


async def http_post(url: str, **kwargs):
    return await asyncio.to_thread(requests.post, url, **kwargs)


async def http_put(url: str, **kwargs):
    return await asyncio.to_thread(requests.put, url, **kwargs)


async def http_get(url: str, **kwargs):
    return await asyncio.to_thread(requests.get, url, **kwargs)


async def main():
    username = f"ws_order_update_{int(time.time())}"
    password = "SecurePass123!"

    register_resp = await http_post(
        f"{BASE}/auth/register",
        json={"username": username, "password": password},
        timeout=10,
    )
    assert_ok(register_resp, "register")
    token = register_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for asset, amount in (("USDT", 10000.0), ("BTC", 2.0)):
        deposit_resp = await http_post(
            f"{BASE}/deposit",
            json={"asset": asset, "amount": amount},
            headers=headers,
            timeout=10,
        )
        assert_ok(deposit_resp, f"deposit {asset}")

    token_id = f"modify_fill_{int(time.time() * 1_000_000)}"
    received_messages: list[dict] = []
    received_update = None
    update_event = asyncio.Event()

    async def listener(ws):
        nonlocal received_update
        while True:
            raw = await ws.recv()
            message = json.loads(raw)
            received_messages.append(message)
            print("WS:", message, flush=True)
            if message.get("type") == "order_update" and message.get("data", {}).get("token_id") == token_id:
                received_update = message
                update_event.set()

    async with websockets.connect(f"{WS}?token={token}", open_timeout=5, close_timeout=1) as ws:
        welcome = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        print("WELCOME:", welcome, flush=True)

        listener_task = asyncio.create_task(listener(ws))

        create_resp = await http_post(
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
        assert_ok(create_resp, "create open limit")
        print("CREATE:", create_resp.json(), flush=True)

        modify_resp = await http_put(
            f"{BASE}/orders/{token_id}",
            json={"price": 1.0},
            headers=headers,
            timeout=10,
        )
        assert_ok(modify_resp, "modify order")
        print("MODIFY:", modify_resp.json(), flush=True)

        deadline = time.time() + 12
        while time.time() < deadline and not update_event.is_set():
            try:
                await asyncio.wait_for(update_event.wait(), timeout=0.75)
            except asyncio.TimeoutError:
                order_resp = await http_get(
                    f"{BASE}/orders/{token_id}",
                    headers=headers,
                    timeout=10,
                )
                assert_ok(order_resp, "poll order")
                order_data = order_resp.json()
                if order_data["status"] == "filled":
                    print("POLLED ORDER FILLED:", order_data, flush=True)

        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

    final_order_resp = await http_get(
        f"{BASE}/orders/{token_id}",
        headers=headers,
        timeout=10,
    )
    assert_ok(final_order_resp, "get final order")
    final_order = final_order_resp.json()
    print("FINAL ORDER:", final_order, flush=True)

    balance_resp = await http_get(f"{BASE}/balance", headers=headers, timeout=10)
    assert_ok(balance_resp, "get balances")
    balances = balance_resp.json()["balances"]
    negatives = [item for item in balances if item["total"] < 0 or item["available"] < 0 or item["reserved"] < 0]
    print("NEGATIVE BALANCES:", negatives, flush=True)

    print("ORDER UPDATE RECEIVED:", bool(received_update), flush=True)
    print("TOTAL WS MESSAGES:", len(received_messages), flush=True)

    if not received_update:
        raise RuntimeError("order_update was not received over WebSocket")
    if final_order["status"] != "filled":
        raise RuntimeError(f"final order status is {final_order['status']}, expected filled")
    if final_order["filled_quantity"] != final_order["quantity"]:
        raise RuntimeError(
            f"filled_quantity mismatch: {final_order['filled_quantity']} vs {final_order['quantity']}"
        )
    if negatives:
        raise RuntimeError(f"negative balances detected: {negatives}")

    print("SUCCESS: order_update received, filled_quantity is correct, no negative balances", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
