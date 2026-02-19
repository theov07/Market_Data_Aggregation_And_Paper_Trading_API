"""
Authentication service for user management, password hashing, and JWT tokens
"""
from datetime import datetime, timedelta
from typing import Optional
import aiosqlite
from passlib.context import CryptContext
from jose import JWTError, jwt

from src.api.models.auth_models import User, UserCreate
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, DB_PATH

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Handles authentication, user management, and JWT tokens"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        
    async def init_db(self):
        """Initialize database and create users table"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            await db.commit()
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def _create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def _decode_token(self, token: str) -> Optional[str]:
        """Decode JWT token and return username"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            return username
        except JWTError:
            return None
    
    async def create_user(self, user_create: UserCreate) -> User:
        """Create a new user"""
        hashed_password = self._hash_password(user_create.password)
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute(
                    "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
                    (user_create.username, hashed_password)
                )
                await db.commit()
                user_id = cursor.lastrowid
                
                # Fetch the created user
                return await self.get_user_by_id(user_id)
            except aiosqlite.IntegrityError:
                raise ValueError(f"Username '{user_create.username}' already exists")
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, username, hashed_password, created_at, is_active FROM users WHERE username = ?",
                (username.lower(),)
            )
            row = await cursor.fetchone()
            
            if row:
                return User(
                    id=row[0],
                    username=row[1],
                    hashed_password=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    is_active=bool(row[4])
                )
            return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, username, hashed_password, created_at, is_active FROM users WHERE id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                return User(
                    id=row[0],
                    username=row[1],
                    hashed_password=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    is_active=bool(row[4])
                )
            return None
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        user = await self.get_user_by_username(username)
        if not user:
            return None
        if not self._verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user
    
    async def create_token_for_user(self, username: str) -> str:
        """Create JWT token for user"""
        access_token = self._create_access_token(data={"sub": username})
        return access_token
    
    async def get_user_from_token(self, token: str) -> Optional[User]:
        """Get user from JWT token"""
        username = self._decode_token(token)
        if username is None:
            return None
        user = await self.get_user_by_username(username)
        return user
