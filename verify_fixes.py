"""
Final verification test script for the paper trading API.
Tests: filled_quantity persistence, negative balance prevention,
modify order behavior, order state consistency.
"""
import time
import requests
import sys

BASE = "http://localhost:8000"


def assert_ok(resp, ctx: str):
    if resp.status_code >= 400:
        print(f"  FAIL [{ctx}]: HTTP {resp.status_code} -> {resp.text[:200]}")
        sys.exit(1)
    return resp.json()


def check_no_negatives(balances: list, label: str):
    negatives = [
        b for b in balances
        if b["total"] < -0.0001 or b["available"] < -0.0001 or b["reserved"] < -0.0001
    ]
    if negatives:
        print(f"  FAIL [{label}]: NEGATIVE BALANCES: {negatives}")
        return False
    return True


def print_balances(balances: list):
    for b in balances:
        print(f"    {b['asset']:8s}  total={b['total']:.6f}  avail={b['available']:.6f}  resv={b['reserved']:.6f}")


def run_tests():
    ts = int(time.time() * 1000)
    username = f"verify_{ts}"
    password = "SecurePass123!"

    print("\n" + "="*60)
    print("VERIFICATION TEST RUN")
    print("="*60)

    # ---- SETUP ----
    print("\n[1] Register user and deposit funds")
    reg = assert_ok(
        requests.post(f"{BASE}/auth/register", json={"username": username, "password": password}),
        "register"
    )
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  User: {username}  token={token[:20]}...")

    assert_ok(requests.post(f"{BASE}/deposit", json={"asset": "USDT", "amount": 50000}, headers=headers), "deposit USDT")
    assert_ok(requests.post(f"{BASE}/deposit", json={"asset": "BTC", "amount": 3.0}, headers=headers), "deposit BTC")
    bals = assert_ok(requests.get(f"{BASE}/balance", headers=headers), "initial balance")["balances"]
    print("  Initial balances:")
    print_balances(bals)
    assert check_no_negatives(bals, "initial balance"), "STOP"

    # ---- TEST 2: MARKET ORDER (buy) ----
    print("\n[2] Market buy order - immediate fill")
    mkt_token = f"mkt_buy_{ts}"
    order = assert_ok(
        requests.post(f"{BASE}/orders", json={
            "token_id": mkt_token,
            "symbol": "BTCUSDT",
            "side": "buy",
            "order_type": "market",
            "quantity": 0.1,
        }, headers=headers),
        "market buy"
    )
    print(f"  Status={order['status']}  filled_quantity={order['filled_quantity']}  price={order['price']}")
    assert order["status"] == "filled", f"Expected filled, got {order['status']}"
    assert order["filled_quantity"] == 0.1, f"Expected filled_quantity=0.1, got {order['filled_quantity']}"
    print("  PASS: Market buy order filled with correct filled_quantity")

    bals = assert_ok(requests.get(f"{BASE}/balance", headers=headers), "balance after market buy")["balances"]
    print_balances(bals)
    assert check_no_negatives(bals, "after market buy"), "STOP"

    # ---- TEST 3: LIMIT ORDER (below market → stays open) ----
    print("\n[3] Limit buy order (far below market → stays open)")
    lim_token = f"lim_buy_{ts}"
    order = assert_ok(
        requests.post(f"{BASE}/orders", json={
            "token_id": lim_token,
            "symbol": "BTCUSDT",
            "side": "buy",
            "order_type": "limit",
            "price": 1000.0,
            "quantity": 0.5,
        }, headers=headers),
        "limit buy"
    )
    print(f"  Status={order['status']}  reserved=${1000*0.5:.2f}")
    assert order["status"] == "open", f"Expected open, got {order['status']}"

    bals_after_open = assert_ok(requests.get(f"{BASE}/balance", headers=headers), "balance after limit")["balances"]
    print_balances(bals_after_open)
    assert check_no_negatives(bals_after_open, "after open limit"), "STOP"
    usdt_before = next(b for b in bals_after_open if b["asset"] == "USDT")
    assert usdt_before["reserved"] == 500.0, f"Expected reserved=500.0, got {usdt_before['reserved']}"
    print("  PASS: Limit order reserved correct USDT amount")

    # ---- TEST 4: MODIFY ORDER (increase price → more reservation) ----
    print("\n[4] Modify order: increase price 1000→1500 (should lock 250 more USDT)")
    mod = assert_ok(
        requests.put(f"{BASE}/orders/{lim_token}", json={"price": 1500.0}, headers=headers),
        "modify order increase"
    )
    print(f"  After modify: price={mod['price']} qty={mod['quantity']} status={mod['status']}")
    assert mod["price"] == 1500.0, f"Expected price 1500.0 after modify, got {mod['price']}"
    bals_after_mod = assert_ok(requests.get(f"{BASE}/balance", headers=headers), "balance after modify up")["balances"]
    print_balances(bals_after_mod)
    assert check_no_negatives(bals_after_mod, "after modify increase"), "STOP"
    usdt_after_mod = next(b for b in bals_after_mod if b["asset"] == "USDT")
    assert usdt_after_mod["reserved"] == 750.0, f"Expected reserved=750.0, got {usdt_after_mod['reserved']}"
    print("  PASS: Modify increased reservation correctly")

    # ---- TEST 5: MODIFY ORDER (decrease price → release reservation) ----
    print("\n[5] Modify order: decrease price 1500→800 (should release 350 USDT)")
    mod2 = assert_ok(
        requests.put(f"{BASE}/orders/{lim_token}", json={"price": 800.0}, headers=headers),
        "modify order decrease"
    )
    print(f"  After mod2: price={mod2['price']} qty={mod2['quantity']}")
    bals_after_mod2 = assert_ok(requests.get(f"{BASE}/balance", headers=headers), "balance after set lower price")["balances"]
    print_balances(bals_after_mod2)
    assert check_no_negatives(bals_after_mod2, "after modify decrease"), "STOP"
    usdt_after_mod2 = next(b for b in bals_after_mod2 if b["asset"] == "USDT")
    assert usdt_after_mod2["reserved"] == 400.0, f"Expected reserved=400.0, got {usdt_after_mod2['reserved']}"
    print("  PASS: Modify decreased reservation correctly")

    # ---- TEST 6: CANCEL ORDER ----
    print("\n[6] Cancel open limit order → should release all reserved")
    can = assert_ok(
        requests.delete(f"{BASE}/orders/{lim_token}", headers=headers),
        "cancel"
    )
    print(f"  Status after cancel={can['status']}")
    assert can["status"] == "cancelled", f"Expected cancelled, got {can['status']}"
    bals_after_cancel = assert_ok(requests.get(f"{BASE}/balance", headers=headers), "balance after cancel")["balances"]
    print_balances(bals_after_cancel)
    assert check_no_negatives(bals_after_cancel, "after cancel"), "STOP"
    usdt_after_cancel = next(b for b in bals_after_cancel if b["asset"] == "USDT")
    assert usdt_after_cancel["reserved"] == 0.0, f"Expected reserved=0.0, got {usdt_after_cancel['reserved']}"
    print("  PASS: Cancel released all reservations")

    # ---- TEST 7: SELL LIMIT ORDER ----
    print("\n[7] Limit SELL order (far above market → stays open), then cancel")
    sell_token = f"lim_sell_{ts}"
    btc_before = next(b for b in bals_after_cancel if b["asset"] == "BTC")
    order_sell = assert_ok(
        requests.post(f"{BASE}/orders", json={
            "token_id": sell_token,
            "symbol": "BTCUSDT",
            "side": "sell",
            "order_type": "limit",
            "price": 9999999.0,
            "quantity": 0.5,
        }, headers=headers),
        "limit sell"
    )
    print(f"  Status={order_sell['status']}")
    bals_sell = assert_ok(requests.get(f"{BASE}/balance", headers=headers), "balance after sell order")["balances"]
    print_balances(bals_sell)
    assert check_no_negatives(bals_sell, "after sell limit"), "STOP"
    btc_sell = next(b for b in bals_sell if b["asset"] == "BTC")
    assert btc_sell["reserved"] == 0.5, f"Expected BTC reserved=0.5, got {btc_sell['reserved']}"
    print("  PASS: Sell order reserved correct BTC")

    # Cancel sell order
    can_sell = assert_ok(requests.delete(f"{BASE}/orders/{sell_token}", headers=headers), "cancel sell")
    bals_after_sell_cancel = assert_ok(requests.get(f"{BASE}/balance", headers=headers), "balance after sell cancel")["balances"]
    print_balances(bals_after_sell_cancel)
    assert check_no_negatives(bals_after_sell_cancel, "after sell cancel"), "STOP"
    btc_after = next(b for b in bals_after_sell_cancel if b["asset"] == "BTC")
    assert btc_after["reserved"] == 0.0, f"Expected BTC reserved=0.0 after cancel, got {btc_after['reserved']}"
    print("  PASS: Sell cancel released BTC reservation")

    # ---- TEST 8: INVALID ORDERS (should be rejected) ----
    print("\n[8] Rejection tests (should all fail with 400/422)")
    
    rej1 = requests.post(f"{BASE}/orders", json={
        "token_id": f"reject_neg_price_{ts}",
        "symbol": "BTCUSDT", "side": "buy", "order_type": "limit",
        "price": -100.0, "quantity": 0.1
    }, headers=headers)
    assert rej1.status_code in (400, 422), f"Expected rejection for negative price, got {rej1.status_code}"
    print(f"  PASS: Negative price rejected (HTTP {rej1.status_code})")

    rej2 = requests.post(f"{BASE}/orders", json={
        "token_id": f"reject_neg_qty_{ts}",
        "symbol": "BTCUSDT", "side": "buy", "order_type": "limit",
        "price": 50000.0, "quantity": -0.1
    }, headers=headers)
    assert rej2.status_code in (400, 422), f"Expected rejection for negative qty, got {rej2.status_code}"
    print(f"  PASS: Negative quantity rejected (HTTP {rej2.status_code})")

    rej3 = requests.post(f"{BASE}/orders", json={
        "token_id": f"reject_insuf_{ts}",
        "symbol": "BTCUSDT", "side": "buy", "order_type": "limit",
        "price": 999999.0, "quantity": 999.0  # Way too much USDT
    }, headers=headers)
    assert rej3.status_code == 400, f"Expected 400 for insufficient balance, got {rej3.status_code}: {rej3.text}"
    print(f"  PASS: Insufficient balance rejected (HTTP {rej3.status_code})")

    # ---- TEST 9: DUPLICATE TOKEN_ID ----
    print("\n[9] Duplicate token_id should be rejected")
    dup_token = f"dup_test_{ts}"
    first = assert_ok(
        requests.post(f"{BASE}/orders", json={
            "token_id": dup_token, "symbol": "BTCUSDT", "side": "buy",
            "order_type": "limit", "price": 500.0, "quantity": 0.1
        }, headers=headers),
        "first order"
    )
    dup = requests.post(f"{BASE}/orders", json={
        "token_id": dup_token, "symbol": "BTCUSDT", "side": "buy",
        "order_type": "limit", "price": 500.0, "quantity": 0.1
    }, headers=headers)
    assert dup.status_code == 400, f"Expected 400 for duplicate token_id, got {dup.status_code}: {dup.text}"
    print(f"  PASS: Duplicate token_id rejected (HTTP {dup.status_code})")
    # Cancel to clean up
    requests.delete(f"{BASE}/orders/{dup_token}", headers=headers)

    # ---- FINAL BALANCE CHECK ----
    print("\n[10] Final balance check - no negatives")
    final_bals = assert_ok(requests.get(f"{BASE}/balance", headers=headers), "final balance")["balances"]
    print_balances(final_bals)
    assert check_no_negatives(final_bals, "final"), "STOP"
    print("  PASS: All balances non-negative")

    print("\n" + "="*60)
    print("ALL TESTS PASSED")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_tests()
