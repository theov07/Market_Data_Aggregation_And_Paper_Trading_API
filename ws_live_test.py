import asyncio
import json
import time
import requests
import websockets

BASE = "http://localhost:8000"
WS = "ws://localhost:8000/ws"


def assert_ok(resp, ctx: str):
    if resp.status_code >= 400:
        raise RuntimeError(f"{ctx} failed: {resp.status_code} {resp.text}")


async def run_ws_order_tests(token: str, headers: dict):
    open_token = f"ws_open_{int(time.time() * 1_000_000)}"
    rest_mod_token = f"rest_mod_{int(time.time() * 1_000_000)}"

    async with websockets.connect(f"{WS}?token={token}") as ws:
        welcome = await asyncio.wait_for(ws.recv(), timeout=5)
        print("WELCOME:", welcome)

        # 1) WS submit -> WS cancel (exercise order management over WebSocket)
        await ws.send(json.dumps({
            "action": "submit_order",
            "token_id": open_token,
            "symbol": "BTCUSDT",
            "side": "buy",
            "price": 100.0,      # far below market -> should remain open
            "quantity": 0.1,
        }))
        submit_reply = await asyncio.wait_for(ws.recv(), timeout=5)
        print("WS SUBMIT REPLY:", submit_reply)

        await ws.send(json.dumps({
            "action": "cancel_order",
            "token_id": open_token,
        }))
        cancel_reply = await asyncio.wait_for(ws.recv(), timeout=5)
        print("WS CANCEL REPLY:", cancel_reply)

        # 2) Difficulty point: modify open order then fill via engine
        create_resp = requests.post(
            f"{BASE}/orders",
            json={
                "token_id": rest_mod_token,
                "symbol": "BTCUSDT",
                "side": "sell",
                "order_type": "limit",
                "price": 90000.0,   # above market -> open
                "quantity": 0.5,
            },
            headers=headers,
            timeout=10,
        )
        assert_ok(create_resp, "create rest limit")
        print("REST CREATE ORDER:", create_resp.json())

        mod_resp = requests.put(
            f"{BASE}/orders/{rest_mod_token}",
            json={"price": 1.0},    # should cross immediately -> filled by engine
            headers=headers,
            timeout=10,
        )
        assert_ok(mod_resp, "modify rest order")
        print("REST MODIFY ORDER:", mod_resp.json())

        # Wait for order_update websocket event while polling REST status
        found_update = None
        final_status = None
        deadline = time.time() + 10
        while time.time() < deadline:
            # Non-blocking-ish WS receive
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=0.4)
                msg = json.loads(raw)
                if msg.get("type") == "order_update" and msg.get("data", {}).get("token_id") == rest_mod_token:
                    found_update = msg
                    print("WS ORDER_UPDATE:", found_update)
                else:
                    print("WS OTHER MESSAGE:", raw)
            except asyncio.TimeoutError:
                pass

            # Poll order state to ensure script always terminates
            o = requests.get(f"{BASE}/orders/{rest_mod_token}", headers=headers, timeout=5)
            assert_ok(o, "poll order")
            final_status = o.json().get("status")
            if final_status == "filled":
                break

        print("WS ORDER_UPDATE RECEIVED:", bool(found_update))
        print("POLLED FINAL STATUS:", final_status)

    # Final verification by REST
    order_resp = requests.get(f"{BASE}/orders/{rest_mod_token}", headers=headers, timeout=10)
    assert_ok(order_resp, "get final order")
    order = order_resp.json()

    print("FINAL ORDER:", {
        "token_id": order["token_id"],
        "status": order["status"],
        "quantity": order["quantity"],
        "filled_quantity": order["filled_quantity"],
        "price": order["price"],
        "executed_at": order["executed_at"],
    })

    bal_resp = requests.get(f"{BASE}/balance", headers=headers, timeout=10)
    assert_ok(bal_resp, "get balances")
    balances = bal_resp.json()["balances"]
    negatives = [b for b in balances if b["total"] < 0 or b["available"] < 0 or b["reserved"] < 0]
    print("NEGATIVE BALANCES FOR TEST USER:", negatives)


def main():
    # 0) Health check
    docs = requests.get(f"{BASE}/docs", timeout=5)
    assert_ok(docs, "docs health")

    username = f"ws_test_{int(time.time())}"
    password = "SecurePass123!"

    reg = requests.post(
        f"{BASE}/auth/register",
        json={"username": username, "password": password},
        timeout=10,
    )
    assert_ok(reg, "register")

    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    print("REGISTERED USER:", username)

    for asset, amount in (("USDT", 10000.0), ("BTC", 2.0)):
        dep = requests.post(
            f"{BASE}/deposit",
            json={"asset": asset, "amount": amount},
            headers=headers,
            timeout=10,
        )
        assert_ok(dep, f"deposit {asset}")
        print(f"DEPOSIT {asset} OK")

    asyncio.run(run_ws_order_tests(token, headers))


if __name__ == "__main__":
    main()
