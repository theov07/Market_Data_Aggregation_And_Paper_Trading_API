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


def test_update_price():
    headers = setup_account()
    token_id = f"order_{int(time.time())}"
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": token_id,
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 50000.0,
        "quantity": 0.1
    }, headers=headers)
    assert resp.status_code == 201
    
    resp = requests.put(f"{BASE_URL}/orders/{token_id}", json={"price": 51000.0}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()['price'] == 51000.0
    assert resp.json()['quantity'] == 0.1


def test_update_quantity():
    headers = setup_account()
    token_id = f"order_{int(time.time())}"
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": token_id,
        "symbol": "BTCUSDT",
        "side": "sell",
        "price": 70000.0,
        "quantity": 0.5
    }, headers=headers)
    assert resp.status_code == 201
    
    resp = requests.put(f"{BASE_URL}/orders/{token_id}", json={"quantity": 0.8}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()['price'] == 70000.0
    assert resp.json()['quantity'] == 0.8


def test_update_both():
    headers = setup_account()
    token_id = f"order_{int(time.time())}"
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": token_id,
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 60000.0,
        "quantity": 0.2
    }, headers=headers)
    assert resp.status_code == 201
    
    resp = requests.put(f"{BASE_URL}/orders/{token_id}", json={"price": 61000.0, "quantity": 0.3}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()['price'] == 61000.0
    assert resp.json()['quantity'] == 0.3


def test_update_nonexistent():
    headers = setup_account()
    resp = requests.put(f"{BASE_URL}/orders/nonexistent", json={"price": 50000.0}, headers=headers)
    assert resp.status_code == 404


def test_update_cancelled():
    headers = setup_account()
    token_id = f"order_{int(time.time())}"
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": token_id,
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 50000.0,
        "quantity": 0.1
    }, headers=headers)
    assert resp.status_code == 201
    
    requests.delete(f"{BASE_URL}/orders/{token_id}", headers=headers)
    resp = requests.put(f"{BASE_URL}/orders/{token_id}", json={"price": 51000.0}, headers=headers)
    assert resp.status_code == 400


def test_insufficient_balance():
    headers = setup_account()
    token_id = f"order_{int(time.time())}"
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "token_id": token_id,
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 50000.0,
        "quantity": 0.1
    }, headers=headers)
    assert resp.status_code == 201
    
    resp = requests.put(f"{BASE_URL}/orders/{token_id}", json={"quantity": 1000.0}, headers=headers)
    assert resp.status_code == 400


if __name__ == '__main__':
    tests = [
        ("Update price", test_update_price),
        ("Update quantity", test_update_quantity),
        ("Update both", test_update_both),
        ("Nonexistent order", test_update_nonexistent),
        ("Cancelled order", test_update_cancelled),
        ("Insufficient balance", test_insufficient_balance)
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
