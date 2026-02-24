from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ValidationInfo


class DepositRequest(BaseModel):
    asset: str = Field(..., description="Asset to deposit")
    amount: float = Field(..., gt=0, description="Amount to deposit")
    
    @field_validator('asset')
    @classmethod
    def asset_uppercase(cls, v: str) -> str:
        """
        Asset uppercase
        """
        return v.upper()


class OrderCreate(BaseModel):
    token_id: str
    symbol: str
    side: str
    order_type: str = "limit"
    price: Optional[float] = None
    quantity: float
    
    @field_validator('symbol')
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        """
        Symbol uppercase
        """
        return v.upper()
    
    @field_validator('side')
    @classmethod
    def validate_side(cls, v: str) -> str:
        """
        Validate side
        """
        v = v.lower()
        if v not in ['buy', 'sell']:
            raise ValueError("side must be 'buy' or 'sell'")
        return v
    
    @field_validator('order_type')
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        """
        Validate order type
        """
        v = v.lower()
        if v not in ['limit', 'market', 'ioc']:
            raise ValueError("order_type must be 'limit', 'market', or 'ioc'")
        return v
    
    @field_validator('price')
    @classmethod
    def validate_price_for_limit(cls, v: Optional[float], info: ValidationInfo) -> Optional[float]:
        """
        Validate price for limit
        """
        order_type = info.data.get('order_type', 'limit')
        if order_type == 'limit' and v is None:
            raise ValueError("price is required for limit orders")
        return v


class OrderResponse(BaseModel):
    id: int
    user_id: int
    token_id: str
    symbol: str
    side: str
    order_type: str
    price: float
    quantity: float
    filled_quantity: Optional[float] = None
    status: str
    created_at: datetime
    executed_at: Optional[datetime]


class Balance(BaseModel):
    asset: str
    total: float
    available: float
    reserved: float


class BalanceResponse(BaseModel):
    balances: list[Balance]


class DepositResponse(BaseModel):
    asset: str
    amount: float
    new_balance: float


class OrderUpdate(BaseModel):
    price: Optional[float] = None
    quantity: Optional[float] = None
    
    @field_validator('price', 'quantity')
    @classmethod
    def at_least_one_field(cls, v: Optional[float], info: ValidationInfo) -> Optional[float]:
        """
        At least one field must be provided
        """
        if v is None and all(val is None for val in info.data.values()):
            raise ValueError("At least one of 'price' or 'quantity' must be provided")
        return v
