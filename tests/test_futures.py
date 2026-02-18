#!/usr/bin/env python3
"""Quick test for futures WebSocket connection"""
import asyncio
import json
import websockets

async def test_futures():
    uri = "ws://localhost:8000/ws"
    
    async with websockets.connect(uri) as websocket:
        print("✅ Connected to WebSocket")
        
        # Receive welcome message
        welcome = await websocket.recv()
        print(f"✅ Welcome: {json.loads(welcome)['type']}")
        
        # Subscribe to BTCUSDT best_touch
        subscription = {
            "action": "subscribe",
            "data_type": "best_touch",
            "symbol": "BTCUSDT"
        }
        await websocket.send(json.dumps(subscription))
        print(f"📤 Sent subscription: {subscription}")
        
        # Wait for confirmation
        confirm = await websocket.recv()
        print(f"✅ Confirmation: {json.loads(confirm)['type']}")
        
        # Receive a few messages
        print("\n📊 Receiving futures market data...\n")
        for i in range(3):
            message = await websocket.recv()
            data = json.loads(message)
            
            print(f"  {i+1}. Message type: {data['type']}")
            print(f"      Data: {json.dumps(data['data'], indent=2)}")
            
            if data['type'] == 'best_touch':
                bt = data['data']
                if 'binance_bid' in bt and 'okx_ask' in bt:
                    spread = bt['binance_bid'] - bt['okx_ask']
                    print(f"      Futures Spread: ${spread:.2f}")
        
        print("\n✅ Futures WebSocket test successful!")

if __name__ == "__main__":
    asyncio.run(test_futures())
