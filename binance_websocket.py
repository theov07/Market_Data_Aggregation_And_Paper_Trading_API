# testing connection to websocket server binance

import websocket


class BinanceWebSocket:
    def __init__(self, url):
        self.url = url
        self.ws = None

    def on_message(self, ws, message):
        print("Received message:", message)

    def on_error(self, ws, error):
        print("Error:", error)

    def on_close(self, ws):
        print("Connection closed")

    def on_open(self, ws):
        print("Connection opened")

    def connect(self):
        self.ws = websocket.WebSocketApp(self.url,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        self.ws.on_open = self.on_open
        self.ws.run_forever()


if __name__ == "__main__":
    url = "wss://stream.binance.com:9443/ws/btcusdt@trade"
    binance_ws = BinanceWebSocket(url)
    binance_ws.connect()