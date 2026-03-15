import asyncio
import json
import os
import sys
import websockets

BASE = os.getenv("BASE_URL", "http://localhost:8000")
WS = os.getenv("WS_URL", BASE.replace("http://", "ws://").replace("https://", "wss://") + "/ws")


async def main():
    if len(sys.argv) != 2:
        print("Usage: python ws_order_listener.py <jwt_token>")
        raise SystemExit(1)

    token = sys.argv[1]
    async with websockets.connect(f"{WS}?token={token}", open_timeout=5) as ws:
        print("CONNECTED")
        while True:
            raw = await ws.recv()
            try:
                print(json.dumps(json.loads(raw), indent=2))
            except Exception:
                print(raw)


if __name__ == "__main__":
    asyncio.run(main())
