"""
WebSocket endpoint - handles client connections and subscriptions
"""
import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query

from src.api.models.api_models import (
    WebSocketSubscription,
    WebSocketOrderSubmit,
    WebSocketOrderCancel
)
from src.api.models.auth_models import User
from src.api.models.trading_models import OrderCreate
from src.api.services.websocket_manager import WebSocketManager, ClientSubscription
from src.api.services.auth_service import AuthService
from src.api.services.trading_service import TradingService


router = APIRouter()


def get_websocket_manager() -> WebSocketManager:
    """Dependency to get WebSocket manager"""
    from src.api.server import websocket_manager
    return websocket_manager


def get_auth_service() -> AuthService:
    """Dependency to get auth service"""
    from src.api.dependencies import get_auth_service as get_service
    return get_service()


def get_trading_service() -> TradingService:
    """Dependency to get trading service"""
    from src.api.routes.trading import trading_service
    if trading_service is None:
        raise ValueError("Trading service not initialized")
    return trading_service


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
    auth_service: AuthService = Depends(get_auth_service),
    trading_service: TradingService = Depends(get_trading_service)
):
    """
    WebSocket endpoint for client subscriptions and order management
    
    Market data subscriptions (no auth required):
    {
        "action": "subscribe" | "unsubscribe",
        "data_type": "best_touch" | "trade" | "kline" | "ewma",
        "symbol": "BTCUSDT",
        "exchange": "all" | "binance" | "okx",
        "interval": "1m"  // optional, required for kline
    }
    
    Order management (requires authentication via ?token=...):
    {
        "action": "submit_order",
        "token_id": "order_123",
        "symbol": "BTCUSDT",
        "side": "buy" | "sell",
        "price": 50000.0,
        "quantity": 0.1
    }
    {
        "action": "cancel_order",
        "token_id": "order_123"
    }
    """
    # Authenticate user if token provided
    current_user: Optional[User] = None
    if token:
        try:
            current_user = await auth_service.get_user_from_token(token)
        except Exception:
            await websocket.close(code=1008, reason="Invalid authentication token")
            return
    
    # Connect with user_id if authenticated
    user_id = current_user.id if current_user else None
    await ws_manager.connect(websocket, user_id)
    
    try:
        await _send_welcome_message(websocket, current_user)
        
        while True:
            message = await websocket.receive_text()
            await _handle_client_message(
                websocket, message, ws_manager,
                current_user, trading_service
            )
    
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        await _send_error_message(websocket, str(e))
        await ws_manager.disconnect(websocket)


async def _send_welcome_message(websocket: WebSocket, user: Optional[User] = None):
    """Send welcome message to newly connected client"""
    auth_status = f"Authenticated as {user.username}" if user else "Not authenticated"
    message = {
        "type": "info",
        "message": "Connected to market data stream",
        "auth_status": auth_status,
        "instructions": {
            "market_data": "Send subscribe/unsubscribe messages to receive data",
            "orders": "Send submit_order/cancel_order messages (requires authentication)"
        }
    }
    await websocket.send_json(message)


async def _handle_client_message(
    websocket: WebSocket,
    message: str,
    ws_manager: WebSocketManager,
    user: Optional[User],
    trading_service: TradingService
):
    """Handle incoming message from client"""
    try:
        data = json.loads(message)
        action = data.get("action")
        
        if action in ["subscribe", "unsubscribe"]:
            subscription = WebSocketSubscription(**data)
            if action == "subscribe":
                await _handle_subscribe(websocket, subscription, ws_manager)
            else:
                await _handle_unsubscribe(websocket, subscription, ws_manager)
        
        elif action == "submit_order":
            if not user:
                await _send_error_message(websocket, "Authentication required for order submission")
                return
            order_msg = WebSocketOrderSubmit(**data)
            await _handle_submit_order(websocket, order_msg, user, trading_service, ws_manager)
        
        elif action == "cancel_order":
            if not user:
                await _send_error_message(websocket, "Authentication required for order cancellation")
                return
            cancel_msg = WebSocketOrderCancel(**data)
            await _handle_cancel_order(websocket, cancel_msg, user, trading_service, ws_manager)
        
        else:
            await _send_error_message(websocket, f"Unknown action: {action}")
    
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


async def _handle_submit_order(
    websocket: WebSocket,
    order_msg: WebSocketOrderSubmit,
    user: User,
    trading_service: TradingService,
    ws_manager: WebSocketManager
):
    """Handle order submission via WebSocket"""
    try:
        # Create order using trading service
        order_req = OrderCreate(
            token_id=order_msg.token_id,
            symbol=order_msg.symbol,
            side=order_msg.side,
            price=order_msg.price,
            quantity=order_msg.quantity
        )
        
        order_response = await trading_service.create_order(user, order_req)
        
        # Send confirmation to client
        await websocket.send_json({
            "type": "order_submitted",
            "order": {
                "id": order_response.id,
                "token_id": order_response.token_id,
                "symbol": order_response.symbol,
                "side": order_response.side,
                "price": order_response.price,
                "quantity": order_response.quantity,
                "status": order_response.status,
                "created_at": order_response.created_at.isoformat()
            }
        })
        
    except ValueError as e:
        await _send_error_message(websocket, f"Order submission failed: {str(e)}")
    except Exception as e:
        await _send_error_message(websocket, f"Order submission error: {str(e)}")


async def _handle_cancel_order(
    websocket: WebSocket,
    cancel_msg: WebSocketOrderCancel,
    user: User,
    trading_service: TradingService,
    ws_manager: WebSocketManager
):
    """Handle order cancellation via WebSocket"""
    try:
        # Cancel order using trading service
        cancelled_order = await trading_service.cancel_order(user, cancel_msg.token_id)
        
        # Send confirmation to client
        await websocket.send_json({
            "type": "order_cancelled",
            "order": {
                "id": cancelled_order.id,
                "token_id": cancelled_order.token_id,
                "symbol": cancelled_order.symbol,
                "status": cancelled_order.status
            }
        })
        
    except ValueError as e:
        await _send_error_message(websocket, f"Order cancellation failed: {str(e)}")
    except Exception as e:
        await _send_error_message(websocket, f"Order cancellation error: {str(e)}")


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
