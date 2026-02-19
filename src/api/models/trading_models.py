from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class DepositRequest(BaseModel):
    """Model for deposit request"""
    asset: str = Field(..., description="Asset to deposit")
    amount: float = Field(..., gt=0, description="Amount to deposit")
    
    @validator('asset')
    def asset_uppercase(cls, v):
        return v.upper()
    
    class Config:
        schema_extra = {
            "example": {
                "asset": "USDT",
                "amount": 10000.0
            }
        }


class OrderCreate(BaseModel):
    """Model for creating a new order"""
    token_id: str = Field(..., description="Unique order ID")
    symbol: str = Field(..., description="Trading pair")
    side: str = Field(..., description="buy or sell")
    price: float = Field(..., gt=0, description="Limit price")
    quantity: float = Field(..., gt=0, description="Order quantity")
    
    @validator('symbol')
    def symbol_uppercase(cls, v):
        return v.upper()
    
    @validator('side')
    def validate_side(cls, v):
        """Validate that side is either 'buy' or 'sell' (case-insensitive)"""
        v = v.lower()
        if v not in ['buy', 'sell']:
            raise ValueError("side must be 'buy' or 'sell'")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "token_id": "order_123456",
                "symbol": "BTCUSDT",
                "side": "buy",
                "price": 50000.0,
                "quantity": 0.1
            }
        }


class OrderResponse(BaseModel):
    """Model for order details response"""
    id: int
    user_id: int
    token_id: str
    symbol: str
    side: str
    price: float
    quantity: float
    status: str
    created_at: datetime
    executed_at: Optional[datetime]
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "user_id": 42,
                "token_id": "order_123456",
                "symbol": "BTCUSDT",
                "side": "buy",
                "price": 50000.0,
                "quantity": 0.1,
                "status": "open",
                "created_at": "2026-02-19T10:30:00",
                "executed_at": None
            }
        }


class Balance(BaseModel):
    """Model for user balance response"""
    asset: str
    total: float
    available: float
    reserved: float
    
    class Config:
        schema_extra = {
            "example": {
                "asset": "USDT",
                "total": 10000.0,
                "available": 9500.0,
                "reserved": 500.0
            }
        }


class BalanceResponse(BaseModel):
    """Model for balance response containing a list of balances for different assets"""
    balances: list[Balance]
    
    class Config:
        schema_extra = {
            "example": {
                "balances": [
                    {
                        "asset": "USDT",
                        "total": 10000.0,
                        "available": 9500.0,
                        "reserved": 500.0
                    },
                    {
                        "asset": "BTC",
                        "total": 0.05,
                        "available": 0.05,
                        "reserved": 0.0
                    }
                ]
            }
        }


class DepositResponse(BaseModel):
    """Model for deposit response"""
    asset: str
    amount: float
    new_balance: float
    
    class Config:
        schema_extra = {
            "example": {
                "asset": "USDT",
                "amount": 10000.0,
                "new_balance": 10000.0
            }
        }
