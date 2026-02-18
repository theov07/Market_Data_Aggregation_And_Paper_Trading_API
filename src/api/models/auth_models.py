"""
Authentication data models
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class UserCreate(BaseModel):
    """Model for user registration"""
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username contains only alphanumeric and underscore"""
        if not v.replace('_', '').isalnum():
            raise ValueError('Username must contain only letters, numbers, and underscores')
        return v.lower()  # Store usernames in lowercase
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "trader_123",
                "password": "securePassword123"
            }
        }


class UserLogin(BaseModel):
    """Model for user login"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    
    @validator('username')
    def lowercase_username(cls, v):
        """Convert username to lowercase for case-insensitive login"""
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "trader_123",
                "password": "securePassword123"
            }
        }


class Token(BaseModel):
    """JWT token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    username: str = Field(..., description="Authenticated username")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "username": "trader_123"
            }
        }


class User(BaseModel):
    """Internal user model"""
    id: int
    username: str
    hashed_password: str
    created_at: datetime
    is_active: bool = True


class TokenData(BaseModel):
    """Data stored in JWT token"""
    username: Optional[str] = None
