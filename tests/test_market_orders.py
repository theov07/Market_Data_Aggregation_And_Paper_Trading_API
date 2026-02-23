import requests
import time

BASE_URL = "http://localhost:8000"


def setup_account():
    username = f"test_{int(time.time())}"
    password = "testpass"
    
    requests.post(f"{BASE_URL}/auth/register", json={"username": username, "password": password})
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    requests.post(f"{BASE_URL}/deposit", json={"asset": "USDT", "amount": 100000.0}, headers=headers)
    requests.post(f"{BASE_URL}/deposit", json={"asset": "BTC", "amount": 10.0}, headers=headers)
    
    return headers


def test_market_buy():
    headers = setup_account()
    token_id = f"order_{int(time.time())}"
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": token_id,
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "market",
        "quantity": 0.1
    }, headers=headers)
    
    assert resp.status_code == 201
    order = resp.json()
    assert order['status'] == 'filled'
    assert order['order_type'] == 'market'
    assert order['executed_at'] is not None


def test_market_sell():
    headers = setup_account()
    token_id = f"order_{int(time.time())}"
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": token_id,
        "symbol": "BTCUSDT",
        "side": "sell",
        "order_type": "market",
        "quantity": 0.1
    }, headers=headers)
    
    assert resp.status_code == 201
    order = resp.json()
    assert order['status'] == 'filled'
    assert order['executed_at'] is not None


def test_limit_order_still_works():
    headers = setup_account()
    token_id = f"order_{int(time.time())}"
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": token_id,
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "limit",
        "price": 50000.0,
        "quantity": 0.1
    }, headers=headers)
    
    assert resp.status_code == 201
    order = resp.json()
    assert order['status'] == 'open'
    assert order['order_type'] == 'limit'


def test_market_insufficient_balance():
    headers = setup_account()
    token_id = f"order_{int(time.time())}"
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": token_id,
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "market",
        "quantity": 10000.0
    }, headers=headers)
    
    assert resp.status_code == 400


if __name__ == '__main__':
    time.sleep(5)  # Wait for market data
    
    tests = [
        ("Market buy", test_market_buy),
        ("Market sell", test_market_sell),
        ("Limit order", test_limit_order_still_works),
        ("Insufficient balance", test_market_insufficient_balance)
    ]
    
    passed = failed = 0
    for name, test in tests:
        try:
            test()
            print(f"PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {name} - {e}")
            failed += 1
    
    print(f"\n{passed}/{len(tests)} tests passed")
