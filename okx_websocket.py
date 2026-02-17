# testing connection to websocket server OKX

import websocket
import json


class OKXWebSocket:
    def __init__(self, url):
        self.url = url
        self.ws = None

    def on_message(self, ws, message):
        print("Received message:", message)

    def on_error(self, ws, error):
        print("Error:", error)

    def on_close(self, ws, close_status_code, close_msg):
        print("Connection closed")

    def on_open(self, ws):
        print("Connection opened")
        # Subscribe to BTC-USDT trades
        subscribe_message = {
            "op": "subscribe",
            "args": [
                {
                    "channel": "trades",
                    "instId": "BTC-USDT"
                }
            ]
        }
        ws.send(json.dumps(subscribe_message))
        print("Subscription message sent")

    def connect(self):
        self.ws = websocket.WebSocketApp(self.url,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close,
                                         on_open=self.on_open)
        self.ws.run_forever()


if __name__ == "__main__":
    url = "wss://ws.okx.com:8443/ws/v5/public"
    okx_ws = OKXWebSocket(url)
    okx_ws.connect()
