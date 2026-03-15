import asyncio
from datetime import datetime
from typing import Optional, List
import aiosqlite

from src.api.models.trading_models import (
    DepositRequest, OrderCreate, OrderResponse, 
    Balance, DepositResponse, OrderUpdate
)
from src.api.models.auth_models import User
from config import SYMBOLS, DB_PATH


class TradingService:
    
    def __init__(self, db_path: str = DB_PATH, best_touch_aggregator=None):
        """Init"""
        self.db_path = db_path
        self._balance_locks = {}
        self.best_touch_aggregator = best_touch_aggregator
        
    def _get_balance_lock(self, user_id: int) -> asyncio.Lock:
        """ get balance lock"""
        if user_id not in self._balance_locks:
            self._balance_locks[user_id] = asyncio.Lock()
        return self._balance_locks[user_id]
    
    async def init_db(self):
        """Init db"""
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
                    order_type TEXT NOT NULL DEFAULT 'limit',
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    filled_quantity REAL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    CHECK (side IN ('buy', 'sell')),
                    CHECK (order_type IN ('limit', 'market', 'ioc')),
                    CHECK (status IN ('open', 'filled', 'cancelled', 'partially_filled'))
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
        """Deposit"""
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
        """Get balance"""
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
        """is valid asset"""
        available_assets = self._get_available_assets()
        return asset.upper() in available_assets
    
    def _get_available_assets(self) -> List[str]:
        """get available assets"""
        assets = set()
        for symbol in SYMBOLS:
            if "USDT" in symbol:
                base = symbol.replace("USDT", "")
                assets.add(base)
                assets.add("USDT")
        return sorted(list(assets))
    
    async def create_order(self, user: User, order_req: OrderCreate) -> OrderResponse:
        """Create order"""
        if order_req.symbol not in SYMBOLS:
            raise ValueError(
                f"Invalid symbol '{order_req.symbol}'. "
                f"Available symbols: {', '.join(SYMBOLS)}"
            )
        
        # For market orders or IOC, get current best touch price
        execution_price = order_req.price
        available_at_best_touch = None  # Will hold available qty from book for IOC
        is_immediate = order_req.order_type in ['market', 'ioc']
        
        if is_immediate:
            if not self.best_touch_aggregator:
                raise ValueError(f"{order_req.order_type.upper()} orders not available: market data service not initialized")
            
            best_touch = self.best_touch_aggregator.get_best_touch(order_req.symbol)
            if not best_touch:
                raise ValueError(f"Market data not available for {order_req.symbol}")
            
            # Buy at best ask, sell at best bid
            if order_req.side == 'buy':
                execution_price = best_touch.best_ask_price
                available_at_best_touch = best_touch.best_ask_quantity
            else:
                execution_price = best_touch.best_bid_price
                available_at_best_touch = best_touch.best_bid_quantity
        
        # IOC orders fill up to the available quantity at best touch; market orders fill in full
        if order_req.order_type == 'ioc' and available_at_best_touch is not None:
            filled_quantity = min(order_req.quantity, available_at_best_touch)
        else:
            filled_quantity = order_req.quantity
        
        if order_req.side == 'buy':
            required_asset = 'USDT'
            required_amount = execution_price * filled_quantity
        else:
            required_asset = order_req.symbol.replace('USDT', '')
            required_amount = filled_quantity
        
        # For sell orders, calculate USDT received separately
        usdt_amount = execution_price * filled_quantity if order_req.side == 'sell' else None
        
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
                
                # For market orders and IOC: execute immediately
                if is_immediate:
                    # Deduct funds directly (no reservation for immediate orders)
                    if order_req.side == 'buy':
                        # Deduct USDT, add base asset
                        debit_cursor = await db.execute(
                            """UPDATE balances 
                               SET available = available - ?,
                                   total = total - ?,
                                   updated_at = CURRENT_TIMESTAMP
                               WHERE user_id = ? AND asset = ?
                                 AND available >= ?
                                 AND total >= ?""",
                            (required_amount, required_amount, user.id, 'USDT', required_amount, required_amount)
                        )
                        if debit_cursor.rowcount == 0:
                            raise ValueError("Insufficient USDT balance during execution")
                        
                        # Add base asset
                        base_asset = order_req.symbol.replace('USDT', '')
                        cursor = await db.execute(
                            "SELECT total FROM balances WHERE user_id = ? AND asset = ?",
                            (user.id, base_asset)
                        )
                        if await cursor.fetchone():
                            await db.execute(
                                """UPDATE balances 
                                   SET total = total + ?,
                                       available = available + ?,
                                       updated_at = CURRENT_TIMESTAMP
                                   WHERE user_id = ? AND asset = ?""",
                                (filled_quantity, filled_quantity, user.id, base_asset)
                            )
                        else:
                            await db.execute(
                                """INSERT INTO balances (user_id, asset, total, available, reserved)
                                   VALUES (?, ?, ?, ?, 0)""",
                                (user.id, base_asset, filled_quantity, filled_quantity)
                            )
                    else:  # sell
                        # Deduct base asset, add USDT
                        base_asset = order_req.symbol.replace('USDT', '')
                        debit_cursor = await db.execute(
                            """UPDATE balances 
                               SET available = available - ?,
                                   total = total - ?,
                                   updated_at = CURRENT_TIMESTAMP
                               WHERE user_id = ? AND asset = ?
                                 AND available >= ?
                                 AND total >= ?""",
                            (filled_quantity, filled_quantity, user.id, base_asset, filled_quantity, filled_quantity)
                        )
                        if debit_cursor.rowcount == 0:
                            raise ValueError(f"Insufficient {base_asset} balance during execution")
                        
                        # Add USDT
                        cursor = await db.execute(
                            "SELECT total FROM balances WHERE user_id = ? AND asset = ?",
                            (user.id, 'USDT')
                        )
                        if await cursor.fetchone():
                            await db.execute(
                                """UPDATE balances 
                                   SET total = total + ?,
                                       available = available + ?,
                                       updated_at = CURRENT_TIMESTAMP
                                   WHERE user_id = ? AND asset = ?""",
                                (usdt_amount, usdt_amount, user.id, 'USDT')
                            )
                        else:
                            await db.execute(
                                """INSERT INTO balances (user_id, asset, total, available, reserved)
                                   VALUES (?, ?, ?, ?, 0)""",
                                (user.id, 'USDT', usdt_amount, usdt_amount)
                            )
                    
                    # Determine final status for IOC
                    if order_req.order_type == 'ioc':
                        if filled_quantity >= order_req.quantity:
                            final_status = 'filled'  # Fully filled
                        elif filled_quantity > 0:
                            final_status = 'partially_filled'  # Partial fill
                        else:
                            final_status = 'cancelled'  # No fill
                    else:  # market
                        final_status = 'filled'
                    
                    # Create order as filled/partially_filled
                    cursor = await db.execute(
                        """INSERT INTO orders 
                           (user_id, token_id, symbol, side, order_type, price, quantity, filled_quantity, status, executed_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                        (user.id, order_req.token_id, order_req.symbol, 
                         order_req.side, order_req.order_type, execution_price, order_req.quantity, filled_quantity, final_status)
                    )
                else:
                    # Limit order: reserve funds
                    reserve_cursor = await db.execute(
                        """UPDATE balances 
                           SET available = available - ?,
                               reserved = reserved + ?,
                               updated_at = CURRENT_TIMESTAMP
                           WHERE user_id = ? AND asset = ?
                             AND available >= ?""",
                        (required_amount, required_amount, user.id, required_asset, required_amount)
                    )
                    if reserve_cursor.rowcount == 0:
                        raise ValueError(
                            f"Insufficient {required_asset} balance for reservation"
                        )
                    
                    # Create order as 'open'
                    cursor = await db.execute(
                        """INSERT INTO orders 
                           (user_id, token_id, symbol, side, order_type, price, quantity, status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, 'open')""",
                        (user.id, order_req.token_id, order_req.symbol, 
                         order_req.side, order_req.order_type, execution_price, order_req.quantity)
                    )
                
                await db.commit()
                order_id = cursor.lastrowid
                
                return await self.get_order_by_id(order_id)
    
    async def get_order(self, user: User, token_id: str) -> Optional[OrderResponse]:
        """Get order"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, user_id, token_id, symbol, side, order_type, price, quantity, 
                          filled_quantity, status, created_at, executed_at
                   FROM orders 
                   WHERE token_id = ? AND user_id = ?""",
                (token_id, user.id)
            )
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_order_response(row)
    
    async def get_order_by_id(self, order_id: int) -> OrderResponse:
        """Get order by id"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, user_id, token_id, symbol, side, order_type, price, quantity,
                          filled_quantity, status, created_at, executed_at
                   FROM orders WHERE id = ?""",
                (order_id,)
            )
            row = await cursor.fetchone()
            return self._row_to_order_response(row)
    
    async def cancel_order(self, user: User, token_id: str) -> OrderResponse:
        """Cancel order"""
        async with self._get_balance_lock(user.id):
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute(
                    """SELECT id, symbol, side, order_type, price, quantity, status
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
                order_type = row['order_type']
                price = row['price']
                quantity = row['quantity']
                
                if side == 'buy':
                    reserved_asset = 'USDT'
                    reserved_amount = price * quantity
                else:
                    reserved_asset = symbol.replace('USDT', '')
                    reserved_amount = quantity
                
                cancel_cursor = await db.execute(
                    """UPDATE orders 
                       SET status = 'cancelled'
                       WHERE id = ? AND status = 'open'""",
                    (order_id,)
                )

                if cancel_cursor.rowcount == 0:
                    raise ValueError("Order is no longer open and cannot be cancelled")

                release_cursor = await db.execute(
                    """UPDATE balances 
                       SET available = available + ?,
                           reserved = reserved - ?,
                           updated_at = CURRENT_TIMESTAMP
                       WHERE user_id = ? AND asset = ?
                         AND reserved >= ?""",
                    (reserved_amount, reserved_amount, user.id, reserved_asset, reserved_amount)
                )

                if release_cursor.rowcount == 0:
                    await db.rollback()
                    raise ValueError(
                        f"Inconsistent reserved {reserved_asset} balance during cancellation"
                    )
                
                await db.commit()
                
                return await self.get_order_by_id(order_id)
    
    async def update_order(self, user: User, token_id: str, order_update: OrderUpdate) -> OrderResponse:
        """Update order"""
        if order_update.price is None and order_update.quantity is None:
            raise ValueError("At least one of 'price' or 'quantity' must be provided")
        
        async with self._get_balance_lock(user.id):
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Get current order
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
                        f"Cannot modify order with status '{row['status']}'. "
                        f"Only 'open' orders can be modified."
                    )
                
                order_id = row['id']
                symbol = row['symbol']
                side = row['side']
                old_price = row['price']
                old_quantity = row['quantity']
                
                # Determine new values
                new_price = order_update.price if order_update.price is not None else old_price
                new_quantity = order_update.quantity if order_update.quantity is not None else old_quantity
                
                # Calculate old and new reserved amounts
                if side == 'buy':
                    reserved_asset = 'USDT'
                    old_reserved = old_price * old_quantity
                    new_reserved = new_price * new_quantity
                else:  # sell
                    reserved_asset = symbol.replace('USDT', '')
                    old_reserved = old_quantity
                    new_reserved = new_quantity
                
                reserved_delta = new_reserved - old_reserved
                
                # Check if user has enough balance if reservation increases
                if reserved_delta > 0:
                    cursor = await db.execute(
                        "SELECT available FROM balances WHERE user_id = ? AND asset = ?",
                        (user.id, reserved_asset)
                    )
                    balance_row = await cursor.fetchone()
                    
                    if not balance_row or balance_row['available'] < reserved_delta:
                        available = balance_row['available'] if balance_row else 0.0
                        raise ValueError(
                            f"Insufficient {reserved_asset} balance. "
                            f"Additional required: {reserved_delta:.8f}, Available: {available:.8f}"
                        )
                
                # Update order only if still open (prevents races with execution engine)
                order_cursor = await db.execute(
                    """UPDATE orders 
                       SET price = ?, quantity = ?
                       WHERE id = ? AND status = 'open'""",
                    (new_price, new_quantity, order_id)
                )

                if order_cursor.rowcount == 0:
                    raise ValueError("Order is no longer open and cannot be modified")

                # Update balance reservations safely
                if reserved_delta > 0:
                    balance_cursor = await db.execute(
                        """UPDATE balances 
                           SET available = available - ?,
                               reserved = reserved + ?,
                               updated_at = CURRENT_TIMESTAMP
                           WHERE user_id = ? AND asset = ?
                             AND available >= ?""",
                        (reserved_delta, reserved_delta, user.id, reserved_asset, reserved_delta)
                    )
                elif reserved_delta < 0:
                    release_amount = -reserved_delta
                    balance_cursor = await db.execute(
                        """UPDATE balances 
                           SET available = available - ?,
                               reserved = reserved + ?,
                               updated_at = CURRENT_TIMESTAMP
                           WHERE user_id = ? AND asset = ?
                             AND reserved >= ?""",
                        (reserved_delta, reserved_delta, user.id, reserved_asset, release_amount)
                    )
                else:
                    balance_cursor = None

                if balance_cursor is not None and balance_cursor.rowcount == 0:
                    await db.rollback()
                    raise ValueError(
                        f"Inconsistent {reserved_asset} reservation during order modification"
                    )
                
                await db.commit()
                
                return await self.get_order_by_id(order_id)
    
    async def get_open_orders(self) -> List[OrderResponse]:
        """Get open orders"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, user_id, token_id, symbol, side, order_type, price, quantity,
                          filled_quantity, status, created_at, executed_at
                   FROM orders 
                   WHERE status = 'open'
                   ORDER BY created_at ASC"""
            )
            rows = await cursor.fetchall()
            
            return [self._row_to_order_response(row) for row in rows]
    
    def _row_to_order_response(self, row) -> OrderResponse:
        """row to order response"""
        return OrderResponse(
            id=row['id'],
            user_id=row['user_id'],
            token_id=row['token_id'],
            symbol=row['symbol'],
            side=row['side'],
            order_type=row['order_type'],
            price=row['price'],
            quantity=row['quantity'],
            filled_quantity=row['filled_quantity'] if row['filled_quantity'] is not None else None,
            status=row['status'],
            created_at=datetime.fromisoformat(row['created_at']),
            executed_at=datetime.fromisoformat(row['executed_at']) if row['executed_at'] else None
        )

