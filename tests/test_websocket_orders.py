#!/usr/bin/env python3
"""
Test script for WebSocket order management
Demonstrates submit_order and cancel_order via WebSocket
"""
import asyncio
import json
import requests
import websockets
import time


BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"


def register_and_login(username: str, password: str) -> str:
    """Register user and get JWT token"""
    # Register
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={"username": username, "password": password}
    )
    print(f"✓ Registered: {response.status_code}")
    
    # Login
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password}
    )
    token = response.json()["access_token"]
    print(f"✓ Logged in as {username}")
    return token


def deposit_funds(token: str, asset: str, amount: float):
    """Deposit funds"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/deposit",
        json={"asset": asset, "amount": amount},
        headers=headers
    )
    print(f"✓ Deposited {amount} {asset}")
    return response.json()


async def test_websocket_orders():
    """Test WebSocket order submission and updates"""
    print("\n" + "="*60)
    print("  WEBSOCKET ORDER MANAGEMENT TEST")
    print("="*60 + "\n")
    
    # Setup: Register and deposit funds
    username = f"ws_trader_{int(time.time())}"
    password = "testpass123"
    
    token = register_and_login(username, password)
    deposit_funds(token, "USDT", 100000.0)
    
    print(f"\n{'='*60}")
    print("  CONNECTING TO WEBSOCKET WITH AUTH")
    print("="*60 + "\n")
    
    # Connect to WebSocket with authentication
    ws_url_with_token = f"{WS_URL}?token={token}"
    
    async with websockets.connect(ws_url_with_token) as websocket:
        # Receive welcome message
        welcome = await websocket.recv()
        print(f"📩 {json.loads(welcome)}\n")
        
        # Subscribe to best_touch to see market data
        print("Subscribing to market data...")
        await websocket.send(json.dumps({
            "action": "subscribe",
            "data_type": "best_touch",
            "symbol": "BTCUSDT",
            "exchange": "all"
        }))
        
        # Wait for subscription confirmation
        msg = await websocket.recv()
        print(f"✓ {json.loads(msg)}\n")
        
        # Wait a bit for market data to flow
        print("Waiting for market data (5 seconds)...")
        await asyncio.sleep(5)
        
        # Drain any market data messages
        try:
            while True:
                msg = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                data = json.loads(msg)
                if data["type"] == "best_touch":
                    print(f"📊 Best touch: Bid ${data['data']['bid_price']:.2f}, Ask ${data['data']['ask_price']:.2f}")
                    break
        except asyncio.TimeoutError:
            pass
        
        # Unsubscribe from best_touch to reduce noise
        print("Unsubscribing from market data to reduce noise...")
        await websocket.send(json.dumps({
            "action": "unsubscribe",
            "data_type": "best_touch",
            "symbol": "BTCUSDT",
            "exchange": "all"
        }))
        
        # Wait for unsubscribe confirmation (skip remaining best_touch)
        for _ in range(20):
            msg = await websocket.recv()
            data = json.loads(msg)
            if data["type"] == "confirmation" and data.get("action") == "unsubscribed":
                print(f"✓ {data}\n")
                break
        
        # Drain any remaining queued best_touch messages
        await asyncio.sleep(0.5)
        try:
            while True:
                await asyncio.wait_for(websocket.recv(), timeout=0.05)
        except asyncio.TimeoutError:
            pass  # No more queued messages
        
        print(f"\n{'='*60}")
        print("  SUBMITTING ORDER VIA WEBSOCKET")
        print("="*60 + "\n")
        
        # Submit order via WebSocket
        order_token_id = f"ws_order_{int(time.time())}"
        order_message = {
            "action": "submit_order",
            "token_id": order_token_id,
            "symbol": "BTCUSDT",
            "side": "buy",
            "price": 50000.0,  # Below market to not execute immediately
            "quantity": 0.1
        }
        
        print(f"Submitting order: {order_token_id}")
        await websocket.send(json.dumps(order_message))
        
        # Wait for order submission confirmation (skip market data messages)
        order_response = None
        for i in range(50):  # Try up to 50 messages (more market data might be flowing)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                data = json.loads(response)
                if data["type"] == "order_submitted":
                    order_response = data
                    break
            except asyncio.TimeoutError:
                break
        
        if not order_response:
            print("❌ No order confirmation received")
            return
        
        print(f"\n✓ Order submitted:")
        print(f"  Type: {order_response['type']}")
        print(f"  Order ID: {order_response['order']['id']}")
        print(f"  Token ID: {order_response['order']['token_id']}")
        print(f"  Status: {order_response['order']['status']}")
        print(f"  Price: ${order_response['order']['price']:,.2f}")
        print(f"  Quantity: {order_response['order']['quantity']} BTC")
        
        print(f"\n{'='*60}")
        print("  MONITORING FOR ORDER UPDATES")
        print("="*60 + "\n")
        
        # Monitor for order updates (execution or timeout)
        print("Listening for order updates (10 seconds)...")
        try:
            for i in range(20):  # 10 seconds
                msg = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                data = json.loads(msg)
                
                if data["type"] == "order_update":
                    print(f"\n🔔 ORDER UPDATE RECEIVED:")
                    print(f"  Token ID: {data['data']['token_id']}")
                    print(f"  Status: {data['data']['status']}")
                    print(f"  Execution Price: ${data['data'].get('execution_price', 'N/A')}")
                    if data['data']['status'] == 'filled':
                        print("  ✅ ORDER FILLED!")
                        break
                elif data["type"] == "best_touch":
                    # Market data still flowing
                    pass
        except asyncio.TimeoutError:
            print("  (no updates yet)")
        
        print(f"\n{'='*60}")
        print("  CANCELLING ORDER VIA WEBSOCKET")
        print("="*60 + "\n")
        
        # Cancel order via WebSocket
        cancel_message = {
            "action": "cancel_order",
            "token_id": order_token_id
        }
        
        print(f"Cancelling order: {order_token_id}")
        await websocket.send(json.dumps(cancel_message))
        
        # Wait for cancellation confirmation (skip market data messages)
        cancel_response = None
        for _ in range(10):  # Try up to 10 messages
            response = await websocket.recv()
            data = json.loads(response)
            if data["type"] == "order_cancelled":
                cancel_response = data
                break
        
        if not cancel_response:
            print("❌ No cancellation confirmation received")
            return
        
        print(f"\n✓ Order cancelled:")
        print(f"  Type: {cancel_response['type']}")
        print(f"  Token ID: {cancel_response['order']['token_id']}")
        print(f"  Status: {cancel_response['order']['status']}")
        
        print(f"\n{'='*60}")
        print("  ✅ WEBSOCKET ORDER TEST COMPLETED")
        print("="*60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(test_websocket_orders())
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
