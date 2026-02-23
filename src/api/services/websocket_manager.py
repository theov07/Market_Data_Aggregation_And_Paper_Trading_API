"""
WebSocket connection manager for client subscriptions
"""
import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket


class ClientSubscription:
    """Represents a single client subscription"""
    
    def __init__(
        self,
        data_type: str,
        symbol: str,
        exchange: str = "all",
        interval: str | None = None
    ):
        self.data_type = data_type
        self.symbol = symbol
        self.exchange = exchange
        self.interval = interval
    
    def get_key(self) -> str:
        """Generate unique subscription key"""
        parts = [self.data_type, self.symbol, self.exchange]
        if self.interval:
            parts.append(self.interval)
        return ":".join(parts)
    
    def matches(self, data_type: str, symbol: str, exchange: str, interval: str | None = None) -> bool:
        """Check if subscription matches given criteria"""
        if self.data_type != data_type:
            return False
        if self.symbol != symbol:
            return False
        if self.exchange != "all" and self.exchange != exchange:
            return False
        if self.data_type == "kline" and self.interval != interval:
            return False
        return True


class WebSocketManager:
    """Manages WebSocket connections and subscriptions"""
    
    def __init__(self):
        self._connections: Dict[WebSocket, Set[ClientSubscription]] = {}
        self._user_connections: Dict[int, WebSocket] = {}  # user_id -> websocket
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: int | None = None):
        """Accept new WebSocket connection"""
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = set()
            if user_id is not None:
                self._user_connections[user_id] = websocket
    
    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        async with self._lock:
            if websocket in self._connections:
                del self._connections[websocket]
            
            # Remove from user connections
            user_id_to_remove = None
            for user_id, ws in self._user_connections.items():
                if ws == websocket:
                    user_id_to_remove = user_id
                    break
            if user_id_to_remove:
                del self._user_connections[user_id_to_remove]
    
    async def add_subscription(self, websocket: WebSocket, subscription: ClientSubscription):
        """Add subscription for a client"""
        async with self._lock:
            if websocket in self._connections:
                self._connections[websocket].add(subscription)
    
    async def remove_subscription(self, websocket: WebSocket, subscription_key: str):
        """Remove subscription for a client"""
        async with self._lock:
            if websocket not in self._connections:
                return
            
            self._connections[websocket] = {
                sub for sub in self._connections[websocket]
                if sub.get_key() != subscription_key
            }
    
    async def broadcast(
        self,
        data_type: str,
        symbol: str,
        exchange: str,
        data: dict,
        interval: str | None = None
    ):
        """Broadcast data to all matching subscriptions"""
        message = self._create_message(data_type, data)
        
        async with self._lock:
            disconnected = []
            
            for websocket, subscriptions in self._connections.items():
                if self._should_send(subscriptions, data_type, symbol, exchange, interval):
                    try:
                        await websocket.send_text(message)
                    except Exception:
                        disconnected.append(websocket)
            
            # Clean up disconnected clients
            for websocket in disconnected:
                del self._connections[websocket]
    
    def _create_message(self, data_type: str, data: dict) -> str:
        """Create JSON message for client"""
        import time
        message = {
            "type": data_type,
            "data": data,
            "timestamp": time.time()
        }
        return json.dumps(message)
    
    def _should_send(
        self,
        subscriptions: Set[ClientSubscription],
        data_type: str,
        symbol: str,
        exchange: str,
        interval: str | None
    ) -> bool:
        """Check if any subscription matches the data"""
        for sub in subscriptions:
            if sub.matches(data_type, symbol, exchange, interval):
                return True
        return False
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self._connections)
    
    async def send_order_update(self, user_id: int, order_data: dict):
        """Send order update to a specific user"""
        async with self._lock:
            if user_id not in self._user_connections:
                return  # User not connected via WebSocket
            
            websocket = self._user_connections[user_id]
            message = {
                "type": "order_update",
                "data": order_data,
                "timestamp": __import__('time').time()
            }
            
            try:
                await websocket.send_json(message)
            except Exception:
                # Connection failed, clean up
                if websocket in self._connections:
                    del self._connections[websocket]
                del self._user_connections[user_id]
