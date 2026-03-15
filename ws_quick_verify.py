import asyncio
import json
import time
import requests
import websockets

BASE = "http://localhost:8000"
WS = "ws://localhost:8000/ws"


def main():
    username = f"wsq_{int(time.time())}"
    password = "SecurePass123!"

    reg = requests.post(f"{BASE}/auth/register", json={"username": username, "password": password}, timeout=10)
    reg.raise_for_status()
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    requests.post(f"{BASE}/deposit", json={"asset": "USDT", "amount": 20000}, headers=headers, timeout=10).raise_for_status()
    requests.post(f"{BASE}/deposit", json={"asset": "BTC", "amount": 2}, headers=headers, timeout=10).raise_for_status()

    print("user:", username)

    async def ws_part():
        async with websockets.connect(f"{WS}?token={token}", open_timeout=5) as ws:
            print("welcome:", await asyncio.wait_for(ws.recv(), timeout=5))

            token_id = f"ws_order_{int(time.time()*1_000_000)}"
            await ws.send(json.dumps({
                "action": "submit_order",
                "token_id": token_id,
                "symbol": "BTCUSDT",
                "side": "buy",
                "price": 100.0,
                "quantity": 0.1
            }))
            print("submit:", await asyncio.wait_for(ws.recv(), timeout=5))

            await ws.send(json.dumps({"action": "cancel_order", "token_id": token_id}))
            print("cancel:", await asyncio.wait_for(ws.recv(), timeout=5))

    asyncio.run(ws_part())

    # difficulty-point check: modify then filled_quantity
    test_id = f"mod_fill_{int(time.time()*1_000_000)}"
    c = requests.post(
        f"{BASE}/orders",
        json={
            "token_id": test_id,
            "symbol": "BTCUSDT",
            "side": "sell",
            "order_type": "limit",
            "price": 90000.0,
            "quantity": 0.5
        },
        headers=headers,
        timeout=10,
    )
    c.raise_for_status()

    m = requests.put(
        f"{BASE}/orders/{test_id}",
        json={"price": 1.0},
        headers=headers,
        timeout=10,
    )
    m.raise_for_status()

    # poll execution
    final = None
    for _ in range(20):
        o = requests.get(f"{BASE}/orders/{test_id}", headers=headers, timeout=10)
        o.raise_for_status()
        final = o.json()
        if final["status"] == "filled":
            break
        time.sleep(0.5)

    print("final order:", {
        "status": final["status"],
        "quantity": final["quantity"],
        "filled_quantity": final["filled_quantity"],
    })

    b = requests.get(f"{BASE}/balance", headers=headers, timeout=10)
    b.raise_for_status()
    neg = [x for x in b.json()["balances"] if x["total"] < 0 or x["available"] < 0 or x["reserved"] < 0]
    print("negative balances:", neg)


if __name__ == "__main__":
    main()
