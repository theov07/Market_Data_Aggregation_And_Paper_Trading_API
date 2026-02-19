#!/usr/bin/env python3
import requests
import json
import time
from typing import Dict, Optional

BASE_URL = "http://localhost:8000"

def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")

def print_response(response: requests.Response):
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")
    print()

def register_user(username: str, password: str) -> bool:
    print_section("REGISTRATION")
    
    url = f"{BASE_URL}/auth/register"
    payload = {
        "username": username,
        "password": password
    }
    
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")
    
    response = requests.post(url, json=payload)
    print_response(response)
    
    return response.status_code in [200, 201]

def login_user(username: str, password: str) -> Optional[str]:
    print_section("LOGIN")
    
    url = f"{BASE_URL}/auth/login"
    payload = {
        "username": username,
        "password": password
    }
    
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")
    
    response = requests.post(url, json=payload)
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"Token: {token[:50]}...\n")
        return token
    
    return None

def deposit(token: str, asset: str, amount: float) -> bool:
    print_section("DEPOSIT")
    
    url = f"{BASE_URL}/deposit"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "asset": asset,
        "amount": amount
    }
    
    print(f"POST {url}")
    print(f"Headers: Bearer {token[:30]}...")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")
    
    response = requests.post(url, json=payload, headers=headers)
    print_response(response)
    
    return response.status_code == 200

def get_balance(token: str) -> Dict:
    print_section("GET BALANCE")
    
    url = f"{BASE_URL}/balance"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"GET {url}")
    print(f"Headers: Bearer {token[:30]}...\n")
    
    response = requests.get(url, headers=headers)
    print_response(response)
    
    if response.status_code == 200:
        return response.json()
    return {}

def create_order(token: str, token_id: str, symbol: str, side: str, 
                 price: float, quantity: float) -> bool:
    print_section("CREATE ORDER")
    
    url = f"{BASE_URL}/orders"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "token_id": token_id,
        "symbol": symbol,
        "side": side,
        "price": price,
        "quantity": quantity
    }
    
    print(f"POST {url}")
    print(f"Headers: Bearer {token[:30]}...")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")
    
    response = requests.post(url, json=payload, headers=headers)
    print_response(response)
    
    return response.status_code == 201

def get_order(token: str, token_id: str) -> Dict:
    print_section("GET ORDER")
    
    url = f"{BASE_URL}/orders/{token_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"GET {url}")
    print(f"Headers: Bearer {token[:30]}...\n")
    
    response = requests.get(url, headers=headers)
    print_response(response)
    
    if response.status_code == 200:
        return response.json()
    return {}

def cancel_order(token: str, token_id: str) -> bool:
    print_section("CANCEL ORDER")
    
    url = f"{BASE_URL}/orders/{token_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"DELETE {url}")
    print(f"Headers: Bearer {token[:30]}...\n")
    
    response = requests.delete(url, headers=headers)
    print_response(response)
    
    return response.status_code == 200

def main():
    print("\n" + "=" * 60)
    print("  TEST COMPLET PAPER TRADING SYSTEM")
    print("=" * 60)
    
    username = f"trader_test_{int(time.time())}"
    password = "password123"
    
    if not register_user(username, password):
        print("Registration failed")
        return
    
    token = login_user(username, password)
    if not token:
        print("Login failed")
        return
    
    if not deposit(token, "USDT", 10000.0):
        print("Deposit failed")
        return
    
    balance_data = get_balance(token)
    if not balance_data:
        print("Get balance failed")
        return
    
    order_token_id = f"order_test_{int(time.time())}"
    if not create_order(token, order_token_id, "BTCUSDT", "buy", 50000.0, 0.1):
        print("Create order failed")
        return
    
    print("Waiting 2 seconds...\n")
    time.sleep(2)
    
    order_data = get_order(token, order_token_id)
    if not order_data:
        print("Get order failed")
        return
    
    if order_data.get("status") == "open":
        if not cancel_order(token, order_token_id):
            print("Cancel order failed")
            return
    else:
        print(f"Order already {order_data.get('status')}, skipping cancel")
    
    print_section("FINAL BALANCE CHECK")
    final_balance = get_balance(token)
    
    print_section("TEST SUMMARY")
    print("All tests passed successfully!")
    print(f"Username: {username}")
    print(f"Order Token ID: {order_token_id}\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
