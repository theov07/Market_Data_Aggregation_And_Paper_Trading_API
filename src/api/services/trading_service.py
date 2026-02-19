"""
Trading service for paper trading system
Manages deposits, balances, and orders
"""
import asyncio
from datetime import datetime
from typing import Optional, List
import aiosqlite

from src.api.models.trading_models import (
    DepositRequest, OrderCreate, OrderResponse, 
    Balance, DepositResponse
)
from src.api.models.auth_models import User
from config import SYMBOLS

DB_PATH = "users.db"


class TradingService:
    
    def __init__(self, db_path: str = DB_PATH):
        """Initialize trading service with database path and balance locks"""
        self.db_path = db_path
        self._balance_locks = {}
        
    def _get_balance_lock(self, user_id: int) -> asyncio.Lock:
        """Get or create a lock for a user's balance to ensure thread safety during updates"""
        if user_id not in self._balance_locks:
            self._balance_locks[user_id] = asyncio.Lock()
        return self._balance_locks[user_id]
    
    async def init_db(self):
        """Initialize the database tables for balances and orders"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS balances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    asset TEXT NOT NULL,
                    total REAL NOT NULL DEFAULT 0,
                    available REAL NOT NULL DEFAULT 0,
                    reserved REAL NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, asset)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    CHECK (side IN ('buy', 'sell')),
                    CHECK (status IN ('open', 'filled', 'cancelled'))
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_token_id ON orders(token_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_balances_user_id ON balances(user_id)
            """)
            
            await db.commit()
            print("✅ Trading database tables initialized")
    
    async def deposit(self, user: User, deposit_req: DepositRequest) -> DepositResponse:
        """Handle deposit request: validate asset, update balance, and return new balance info"""
        if not self._is_valid_asset(deposit_req.asset):
            raise ValueError(
                f"Asset '{deposit_req.asset}' is not available. "
                f"Available assets: {self._get_available_assets()}"
            )
        
        async with self._get_balance_lock(user.id):
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT total FROM balances WHERE user_id = ? AND asset = ?",
                    (user.id, deposit_req.asset)
                )
                row = await cursor.fetchone()
                
                if row:
                    new_total = row[0] + deposit_req.amount
                    new_available = new_total
                    
                    await db.execute(
                        """UPDATE balances 
                           SET total = total + ?, 
                               available = available + ?,
                               updated_at = CURRENT_TIMESTAMP
                           WHERE user_id = ? AND asset = ?""",
                        (deposit_req.amount, deposit_req.amount, user.id, deposit_req.asset)
                    )
                else:
                    new_total = deposit_req.amount
                    await db.execute(
                        """INSERT INTO balances (user_id, asset, total, available, reserved)
                           VALUES (?, ?, ?, ?, 0)""",
                        (user.id, deposit_req.asset, new_total, new_total)
                    )
                
                await db.commit()
                
                return DepositResponse(
                    asset=deposit_req.asset,
                    amount=deposit_req.amount,
                    new_balance=new_total
                )
    
    async def get_balance(self, user: User) -> List[Balance]:
        """Get the current balance for all assets of the user"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT asset, total, available, reserved 
                   FROM balances 
                   WHERE user_id = ?
                   ORDER BY asset""",
                (user.id,)
            )
            rows = await cursor.fetchall()
            
            balances = []
            for row in rows:
                balances.append(Balance(
                    asset=row['asset'],
                    total=row['total'],
                    available=row['available'],
                    reserved=row['reserved']
                ))
            
            return balances
    
    def _is_valid_asset(self, asset: str) -> bool:
        """Check if the asset is valid based on available symbols"""
        available_assets = self._get_available_assets()
        return asset.upper() in available_assets
    
    def _get_available_assets(self) -> List[str]:
        """Get a list of available assets based on the defined symbols"""
        assets = set()
        for symbol in SYMBOLS:
            if "USDT" in symbol:
                base = symbol.replace("USDT", "")
                assets.add(base)
                assets.add("USDT")
        return sorted(list(assets))
    
    async def create_order(self, user: User, order_req: OrderCreate) -> OrderResponse:
        """Handle order creation: validate input, check balance, reserve funds, and create order record"""
        if order_req.symbol not in SYMBOLS:
            raise ValueError(
                f"Invalid symbol '{order_req.symbol}'. "
                f"Available symbols: {', '.join(SYMBOLS)}"
            )
        
        if order_req.side == 'buy':
            required_asset = 'USDT'
            required_amount = order_req.price * order_req.quantity
        else:
            required_asset = order_req.symbol.replace('USDT', '')
            required_amount = order_req.quantity
        
        async with self._get_balance_lock(user.id):
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT id FROM orders WHERE token_id = ?",
                    (order_req.token_id,)
                )
                if await cursor.fetchone():
                    raise ValueError(f"Order with token_id '{order_req.token_id}' already exists")
                
                cursor = await db.execute(
                    "SELECT available FROM balances WHERE user_id = ? AND asset = ?",
                    (user.id, required_asset)
                )
                row = await cursor.fetchone()
                
                if not row or row[0] < required_amount:
                    available = row[0] if row else 0.0
                    raise ValueError(
                        f"Insufficient {required_asset} balance. "
                        f"Required: {required_amount:.8f}, Available: {available:.8f}"
                    )
                
                await db.execute(
                    """UPDATE balances 
                       SET available = available - ?,
                           reserved = reserved + ?,
                           updated_at = CURRENT_TIMESTAMP
                       WHERE user_id = ? AND asset = ?""",
                    (required_amount, required_amount, user.id, required_asset)
                )
                
                cursor = await db.execute(
                    """INSERT INTO orders 
                       (user_id, token_id, symbol, side, price, quantity, status)
                       VALUES (?, ?, ?, ?, ?, ?, 'open')""",
                    (user.id, order_req.token_id, order_req.symbol, 
                     order_req.side, order_req.price, order_req.quantity)
                )
                await db.commit()
                order_id = cursor.lastrowid
                
                return await self.get_order_by_id(order_id)
    
    async def get_order(self, user: User, token_id: str) -> Optional[OrderResponse]:
        """Get order details by token_id for the user"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, user_id, token_id, symbol, side, price, quantity, 
                          status, created_at, executed_at
                   FROM orders 
                   WHERE token_id = ? AND user_id = ?""",
                (token_id, user.id)
            )
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_order_response(row)
    
    async def get_order_by_id(self, order_id: int) -> OrderResponse:
        """Get order details by order ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, user_id, token_id, symbol, side, price, quantity,
                          status, created_at, executed_at
                   FROM orders WHERE id = ?""",
                (order_id,)
            )
            row = await cursor.fetchone()
            return self._row_to_order_response(row)
    
    async def cancel_order(self, user: User, token_id: str) -> OrderResponse:
        """Cancel an open order: check status, release reserved funds, and update order status"""
        async with self._get_balance_lock(user.id):
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute(
                    """SELECT id, symbol, side, price, quantity, status
                       FROM orders 
                       WHERE token_id = ? AND user_id = ?""",
                    (token_id, user.id)
                )
                row = await cursor.fetchone()
                
                if not row:
                    raise ValueError(f"Order with token_id '{token_id}' not found")
                
                if row['status'] != 'open':
                    raise ValueError(
                        f"Cannot cancel order with status '{row['status']}'. "
                        f"Only 'open' orders can be cancelled."
                    )
                
                order_id = row['id']
                symbol = row['symbol']
                side = row['side']
                price = row['price']
                quantity = row['quantity']
                
                if side == 'buy':
                    reserved_asset = 'USDT'
                    reserved_amount = price * quantity
                else:
                    reserved_asset = symbol.replace('USDT', '')
                    reserved_amount = quantity
                
                await db.execute(
                    """UPDATE balances 
                       SET available = available + ?,
                           reserved = reserved - ?,
                           updated_at = CURRENT_TIMESTAMP
                       WHERE user_id = ? AND asset = ?""",
                    (reserved_amount, reserved_amount, user.id, reserved_asset)
                )
                
                await db.execute(
                    """UPDATE orders 
                       SET status = 'cancelled'
                       WHERE id = ?""",
                    (order_id,)
                )
                
                await db.commit()
                
                return await self.get_order_by_id(order_id)
    
    async def get_open_orders(self) -> List[OrderResponse]:
        """Get a list of all open orders in the system"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, user_id, token_id, symbol, side, price, quantity,
                          status, created_at, executed_at
                   FROM orders 
                   WHERE status = 'open'
                   ORDER BY created_at ASC"""
            )
            rows = await cursor.fetchall()
            
            return [self._row_to_order_response(row) for row in rows]
    
    def _row_to_order_response(self, row) -> OrderResponse:
        """Convert a database row to an OrderResponse model"""
        return OrderResponse(
            id=row['id'],
            user_id=row['user_id'],
            token_id=row['token_id'],
            symbol=row['symbol'],
            side=row['side'],
            price=row['price'],
            quantity=row['quantity'],
            status=row['status'],
            created_at=datetime.fromisoformat(row['created_at']),
            executed_at=datetime.fromisoformat(row['executed_at']) if row['executed_at'] else None
        )

