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


def test_ioc_small_filled():
    headers = setup_account()
    token_id = f"order_{int(time.time())}"
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": token_id,
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "ioc",
        "quantity": 0.1
    }, headers=headers)
    
    assert resp.status_code == 201
    order = resp.json()
    assert order['status'] == 'filled'
    assert order['filled_quantity'] == 0.1


def test_ioc_large_partial():
    headers = setup_account()
    token_id = f"order_{int(time.time())}"
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": token_id,
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "ioc",
        "quantity": 2.0
    }, headers=headers)
    
    assert resp.status_code == 201
    order = resp.json()
    assert order['status'] == 'partially_filled'
    assert order['filled_quantity'] == 0.5


def test_ioc_sell():
    headers = setup_account()
    token_id = f"order_{int(time.time())}"
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": token_id,
        "symbol": "BTCUSDT",
        "side": "sell",
        "order_type": "ioc",
        "quantity": 0.2
    }, headers=headers)
    
    assert resp.status_code == 201
    order = resp.json()
    assert order['status'] == 'filled'
    assert order['filled_quantity'] == 0.2


def test_ioc_vs_market():
    headers = setup_account()
    
    market_id = f"market_{int(time.time())}"
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": market_id,
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "market",
        "quantity": 0.6
    }, headers=headers)
    assert resp.status_code == 201
    market_order = resp.json()
    
    time.sleep(0.1)
    
    ioc_id = f"ioc_{int(time.time())}"
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": ioc_id,
        "symbol": "BTCUSDT",
        "side": "sell",
        "order_type": "ioc",
        "quantity": 0.6
    }, headers=headers)
    assert resp.status_code == 201
    ioc_order = resp.json()
    
    assert market_order['status'] == 'filled'
    assert ioc_order['status'] in ['filled', 'partially_filled']


if __name__ == '__main__':
    time.sleep(5)  # Wait for market data
    
    tests = [
        ("IOC small fully filled", test_ioc_small_filled),
        ("IOC large partially filled", test_ioc_large_partial),
        ("IOC sell", test_ioc_sell),
        ("IOC vs Market", test_ioc_vs_market)
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
