"""
Test WebSocket client to demonstrate API usage
"""
import asyncio
import json
import websockets


async def test_websocket_client():
    """Connect to WebSocket and subscribe to market data"""
    uri = "ws://localhost:8000/ws"
    
    async with websockets.connect(uri) as websocket:
        # Receive welcome message
        welcome = await websocket.recv()
        print(f"📨 {welcome}\n")
        
        # Subscribe to best touch for BTCUSDT
        subscribe_best_touch = {
            "action": "subscribe",
            "data_type": "best_touch",
            "symbol": "BTCUSDT",
            "exchange": "all"
        }
        await websocket.send(json.dumps(subscribe_best_touch))
        print(f"✉️  Sent: {subscribe_best_touch}")
        
        # Subscribe to trades for ETHUSDT from Binance
        subscribe_trade = {
            "action": "subscribe",
            "data_type": "trade",
            "symbol": "ETHUSDT",
            "exchange": "binance"
        }
        await websocket.send(json.dumps(subscribe_trade))
        print(f"✉️  Sent: {subscribe_trade}")
        
        # Subscribe to 1m klines for SOLUSDT
        subscribe_kline = {
            "action": "subscribe",
            "data_type": "kline",
            "symbol": "SOLUSDT",
            "exchange": "all",
            "interval": "1m"
        }
        await websocket.send(json.dumps(subscribe_kline))
        print(f"✉️  Sent: {subscribe_kline}\n")
        
        # Subscribe to EWMA for BNBUSDT
        subscribe_ewma = {
            "action": "subscribe",
            "data_type": "ewma",
            "symbol": "BNBUSDT",
            "exchange": "okx"
        }
        await websocket.send(json.dumps(subscribe_ewma))
        print(f"✉️  Sent: {subscribe_ewma}\n")
        
        # Receive and display messages
        print("📊 Receiving market data (press Ctrl+C to stop):\n")
        message_count = 0
        
        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                message_count += 1
                _display_message(data, message_count)
                
                # Show only first 50 messages to avoid spam
                if message_count >= 50:
                    print("\n✋ Stopping after 50 messages (remove limit to see more)")
                    break
        
        except KeyboardInterrupt:
            print("\n\n👋 Disconnecting...")


def _display_message(data: dict, count: int):
    """Display received message in a readable format"""
    msg_type = data.get("type", "unknown")
    
    if msg_type == "confirmation":
        print(f"✅ [{count}] Confirmation: {data.get('action')} - {data.get('subscription')}")
    
    elif msg_type == "best_touch":
        info = data.get("data", {})
        symbol = info.get("symbol")
        bid = info.get("bid_price")
        bid_ex = info.get("bid_exchange")
        ask = info.get("ask_price")
        ask_ex = info.get("ask_exchange")
        spread = info.get("spread")
        print(f"💰 [{count}] Best Touch {symbol}: Bid {bid}@{bid_ex} | Ask {ask}@{ask_ex} | Spread {spread}")
    
    elif msg_type == "trade":
        info = data.get("data", {})
        symbol = info.get("symbol")
        exchange = info.get("exchange")
        price = info.get("price")
        quantity = info.get("quantity")
        print(f"🔄 [{count}] Trade {symbol}@{exchange}: {quantity} @ {price}")
    
    elif msg_type == "kline":
        info = data.get("data", {})
        symbol = info.get("symbol")
        interval = info.get("interval")
        close = info.get("close")
        volume = info.get("volume")
        print(f"📈 [{count}] Kline {symbol} {interval}: Close {close} | Volume {volume}")
    
    elif msg_type == "ewma":
        info = data.get("data", {})
        symbol = info.get("symbol")
        exchange = info.get("exchange")
        value = info.get("value")
        print(f"📊 [{count}] EWMA {symbol}@{exchange}: {value}")
    
    elif msg_type == "error":
        print(f"❌ [{count}] Error: {data.get('message')}")
    
    else:
        print(f"ℹ️  [{count}] {msg_type}: {data}")


if __name__ == "__main__":
    print("🚀 Starting WebSocket client test...\n")
    try:
        asyncio.run(test_websocket_client())
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user")
