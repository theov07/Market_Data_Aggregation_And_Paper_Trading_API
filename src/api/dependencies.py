"""
FastAPI dependencies for authentication
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.api.models.auth_models import User
from src.api.services.auth_service import AuthService


# Security scheme for Swagger UI
security = HTTPBearer()

# Global auth service instance (will be set on app startup)
_auth_service: Optional[AuthService] = None


def set_auth_service(service: AuthService):
    """Set the global auth service instance"""
    global _auth_service
    _auth_service = service


def get_auth_service() -> AuthService:
    """Get the auth service instance"""
    if _auth_service is None:
        raise RuntimeError("Auth service not initialized")
    return _auth_service


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    
    Usage in protected routes:
    ```python
    @router.get("/protected")
    async def protected_route(current_user: User = Depends(get_current_user)):
        return {"user": current_user.username}
    ```
    """
    token = credentials.credentials
    
    # Validate token and get user
    user = await auth_service.get_user_from_token(token)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get the current active user.
    This is an alias for get_current_user (already checks is_active).
    """
    return current_user
