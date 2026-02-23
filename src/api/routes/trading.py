from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional

from src.api.models.trading_models import (
    DepositRequest, DepositResponse,
    OrderCreate, OrderResponse,
    BalanceResponse, OrderUpdate
)
from src.api.models.auth_models import User
from src.api.services.trading_service import TradingService
from src.api.dependencies import get_current_user


router = APIRouter(tags=["Trading"])
trading_service: Optional[TradingService] = None


def get_trading_service() -> TradingService:
    """Get trading service"""
    if trading_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trading service not initialized"
        )
    return trading_service


@router.post(
    "/deposit",
    response_model=DepositResponse,
    status_code=status.HTTP_200_OK,
    summary="Deposit funds"
)
async def deposit(
    deposit_req: DepositRequest,
    current_user: User = Depends(get_current_user),
    service: TradingService = Depends(get_trading_service)
):
    try:
        return await service.deposit(current_user, deposit_req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deposit failed: {str(e)}"
        )


@router.get(
    "/balance",
    response_model=BalanceResponse,
    summary="Get account balances"
)
async def get_balance(
    current_user: User = Depends(get_current_user),
    service: TradingService = Depends(get_trading_service)
):
    try:
        balances = await service.get_balance(current_user)
        return BalanceResponse(balances=balances)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve balances: {str(e)}"
        )


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a limit order"
)
async def create_order(
    order_req: OrderCreate,
    current_user: User = Depends(get_current_user),
    service: TradingService = Depends(get_trading_service)
):
    try:
        return await service.create_order(current_user, order_req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order creation failed: {str(e)}"
        )


@router.get(
    "/orders/{token_id}",
    response_model=OrderResponse,
    summary="Get order status"
)
async def get_order(
    token_id: str,
    current_user: User = Depends(get_current_user),
    service: TradingService = Depends(get_trading_service)
):
    try:
        order = await service.get_order(current_user, token_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with token_id '{token_id}' not found"
            )
        return order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve order: {str(e)}"
        )


@router.put(
    "/orders/{token_id}",
    response_model=OrderResponse,
    summary="Update an order"
)
async def update_order(
    token_id: str,
    order_update: OrderUpdate,
    current_user: User = Depends(get_current_user),
    service: TradingService = Depends(get_trading_service)
):
    try:
        return await service.update_order(current_user, token_id, order_update)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order update failed: {str(e)}"
        )


@router.delete(
    "/orders/{token_id}",
    response_model=OrderResponse,
    summary="Cancel an order"
)
async def cancel_order(
    token_id: str,
    current_user: User = Depends(get_current_user),
    service: TradingService = Depends(get_trading_service)
):
    try:
        return await service.cancel_order(current_user, token_id)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order cancellation failed: {str(e)}"
        )
