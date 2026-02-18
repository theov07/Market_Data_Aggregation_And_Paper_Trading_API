"""
Authentication routes: register and login
"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from src.api.models.auth_models import UserCreate, UserLogin, Token
from src.api.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Authentication"])

auth_service: AuthService = None


def get_auth_service() -> AuthService:
    """Dependency to get auth service"""
    return auth_service


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with username and password. Username must be unique.",
    responses={
        201: {
            "description": "User created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "username": "trader_123"
                    }
                }
            }
        },
        400: {
            "description": "Username already exists or validation error",
            "content": {
                "application/json": {
                    "example": {"detail": "Username 'trader_123' already exists"}
                }
            }
        }
    }
)
async def register(
    user_create: UserCreate,
    service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user account.
    
    - **username**: Unique username (3-50 characters, alphanumeric + underscore only)
    - **password**: Password (minimum 6 characters)
    
    Returns JWT access token upon successful registration.
    """
    try:
        # Create user
        user = await service.create_user(user_create)
        
        # Generate token
        access_token = await service.create_token_for_user(user.username)
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            username=user.username
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post(
    "/login",
    response_model=Token,
    summary="Login with username and password",
    description="Authenticate with username and password to receive a JWT access token.",
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "username": "trader_123"
                    }
                }
            }
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid username or password"}
                }
            }
        }
    }
)
async def login(
    user_login: UserLogin,
    service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user and receive JWT access token.
    
    - **username**: Your username
    - **password**: Your password
    
    Returns JWT access token for authenticated requests.
    """
    # Authenticate user
    user = await service.authenticate_user(user_login.username, user_login.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate token
    access_token = await service.create_token_for_user(user.username)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        username=user.username
    )
