"""
WebSocket endpoint - handles client connections and subscriptions
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from src.api.models.api_models import WebSocketSubscription
from src.api.services.websocket_manager import WebSocketManager, ClientSubscription


router = APIRouter()


def get_websocket_manager() -> WebSocketManager:
    """Dependency to get WebSocket manager"""
    from src.api.server import websocket_manager
    return websocket_manager


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """
    WebSocket endpoint for client subscriptions
    
    Clients can send subscription messages to receive real-time data:
    {
        "action": "subscribe" | "unsubscribe",
        "data_type": "best_touch" | "trade" | "kline" | "ewma",
        "symbol": "BTCUSDT",
        "exchange": "all" | "binance" | "okx",
        "interval": "1m"  // optional, required for kline
    }
    """
    await ws_manager.connect(websocket)
    
    try:
        await _send_welcome_message(websocket)
        
        while True:
            # Receive message from client
            message = await websocket.receive_text()
            await _handle_client_message(websocket, message, ws_manager)
    
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        await _send_error_message(websocket, str(e))
        await ws_manager.disconnect(websocket)


async def _send_welcome_message(websocket: WebSocket):
    """Send welcome message to newly connected client"""
    message = {
        "type": "info",
        "message": "Connected to market data stream",
        "instructions": "Send subscribe/unsubscribe messages to receive data"
    }
    await websocket.send_json(message)


async def _handle_client_message(
    websocket: WebSocket,
    message: str,
    ws_manager: WebSocketManager
):
    """Handle incoming message from client"""
    try:
        data = json.loads(message)
        subscription = WebSocketSubscription(**data)
        
        if subscription.action == "subscribe":
            await _handle_subscribe(websocket, subscription, ws_manager)
        elif subscription.action == "unsubscribe":
            await _handle_unsubscribe(websocket, subscription, ws_manager)
    
    except Exception as e:
        await _send_error_message(websocket, f"Invalid message: {str(e)}")


async def _handle_subscribe(
    websocket: WebSocket,
    subscription: WebSocketSubscription,
    ws_manager: WebSocketManager
):
    """Handle subscribe action"""
    # Validate kline interval requirement
    if subscription.data_type == "kline" and not subscription.interval:
        await _send_error_message(websocket, "interval is required for kline subscriptions")
        return
    
    client_sub = ClientSubscription(
        data_type=subscription.data_type,
        symbol=subscription.symbol,
        exchange=subscription.exchange,
        interval=subscription.interval
    )
    
    await ws_manager.add_subscription(websocket, client_sub)
    await _send_confirmation(websocket, "subscribed", client_sub.get_key())


async def _handle_unsubscribe(
    websocket: WebSocket,
    subscription: WebSocketSubscription,
    ws_manager: WebSocketManager
):
    """Handle unsubscribe action"""
    client_sub = ClientSubscription(
        data_type=subscription.data_type,
        symbol=subscription.symbol,
        exchange=subscription.exchange,
        interval=subscription.interval
    )
    
    await ws_manager.remove_subscription(websocket, client_sub.get_key())
    await _send_confirmation(websocket, "unsubscribed", client_sub.get_key())


async def _send_confirmation(websocket: WebSocket, action: str, subscription_key: str):
    """Send confirmation message to client"""
    message = {
        "type": "confirmation",
        "action": action,
        "subscription": subscription_key
    }
    await websocket.send_json(message)


async def _send_error_message(websocket: WebSocket, error: str):
    """Send error message to client"""
    message = {
        "type": "error",
        "message": error
    }
    await websocket.send_json(message)
