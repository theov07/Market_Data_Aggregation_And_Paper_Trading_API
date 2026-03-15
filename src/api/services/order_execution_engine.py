import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict
import aiosqlite

from src.api.models.trading_models import OrderResponse
from src.processors.best_touch import BestTouchAggregator
from config import DB_PATH

logger = logging.getLogger(__name__)


class OrderExecutionEngine:
    
    def __init__(
        self, 
        best_touch_aggregator: BestTouchAggregator,
        websocket_manager=None,  # Optional WebSocketManager
        db_path: str = DB_PATH,
        check_interval: float = 0.5
    ):
        self.best_touch_aggregator = best_touch_aggregator
        self.websocket_manager = websocket_manager
        self.db_path = db_path
        self.check_interval = check_interval
        
        self.running = False
        self._task: Optional[asyncio.Task] = None
        
        self.orders_executed = 0
        self.last_check_time: Optional[datetime] = None
        
        # Order execution locks to prevent double execution
        self._order_locks: Dict[str, asyncio.Lock] = {}
    
    def _get_order_lock(self, token_id: str) -> asyncio.Lock:
        """Get or create a lock for a specific order token_id"""
        if token_id not in self._order_locks:
            self._order_locks[token_id] = asyncio.Lock()
        return self._order_locks[token_id]
    
    async def start(self):
        """Start the order execution engine"""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._execution_loop())
    
    async def stop(self):
        """Stop the order execution engine"""
        if not self.running:
            return
        
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _execution_loop(self):
        """Main loop to check and execute orders"""
        
        while self.running:
            try:
                await self._check_and_execute_orders()
                self.last_check_time = datetime.now(timezone.utc)
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in execution loop: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def _check_and_execute_orders(self):
        """Check open orders and execute if conditions are met"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            cursor = await db.execute(
                """SELECT id, user_id, token_id, symbol, side, price, quantity
                   FROM orders 
                   WHERE status = 'open'
                   ORDER BY created_at ASC"""
            )
            open_orders = await cursor.fetchall()
            
            for order in open_orders:
                try:
                    # Prevent concurrent execution of the same order
                    async with self._get_order_lock(order['token_id']):
                        # Idempotence + freshness: reload full order row within lock
                        cursor = await db.execute(
                            """SELECT id, user_id, token_id, symbol, side, price, quantity, status
                               FROM orders
                               WHERE token_id = ?""",
                            (order['token_id'],)
                        )
                        current_order = await cursor.fetchone()
                        if not current_order or current_order['status'] != 'open':
                            continue  # Already processed
                        
                        await self._try_execute_order(db, current_order)
                except Exception as e:
                    logger.error(
                        f"Error executing order {order['token_id']}: {e}", 
                        exc_info=True
                    )
    
    async def _try_execute_order(self, db: aiosqlite.Connection, order):
        """Check if the order can be executed based on best touch and execute if conditions are met"""
        symbol = order['symbol']
        side = order['side']
        limit_price = order['price']
        
        best_touch = self.best_touch_aggregator.get_best_touch(symbol)
        
        if not best_touch:
            return
        
        should_execute = False
        execution_price = None
        
        if side == 'buy':
            if best_touch.best_ask_price and best_touch.best_ask_price <= limit_price:
                should_execute = True
                execution_price = best_touch.best_ask_price
        else:
            if best_touch.best_bid_price and best_touch.best_bid_price >= limit_price:
                should_execute = True
                execution_price = best_touch.best_bid_price
        
        if should_execute:
            await self._execute_order(
                db=db,
                order_id=order['id'],
                user_id=order['user_id'],
                token_id=order['token_id'],
                symbol=symbol,
                side=side,
                price=order['price'],
                quantity=order['quantity'],
                execution_price=execution_price
            )
    
    async def _execute_order(
        self, 
        db: aiosqlite.Connection,
        order_id: int,
        user_id: int,
        token_id: str,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        execution_price: float
    ):
        """Execute the order: update order status, adjust user balances, and log execution"""
        try:
            base_asset = symbol.replace('USDT', '')
            quote_asset = 'USDT'
            
            if side == 'buy':
                spent_asset = quote_asset
                reserved_amount = price * quantity         # what was locked at order creation
                actual_spent    = execution_price * quantity  # what is really debited
                received_asset  = base_asset
                received_amount = quantity
            else:
                spent_asset     = base_asset
                reserved_amount = quantity                 # BTC locked at order creation
                actual_spent    = quantity                 # same — full BTC qty is sold
                received_asset  = quote_asset
                received_amount = execution_price * quantity  # USDT received at execution price

            cursor = await db.execute(
                """UPDATE orders 
                   SET status = 'filled',
                       filled_quantity = ?,
                       executed_at = CURRENT_TIMESTAMP
                   WHERE id = ? AND status = 'open'""",
                (quantity, order_id)
            )

            # If no row was updated, the order has already been processed
            # by another worker/instance. Do not touch balances again.
            if cursor.rowcount == 0:
                await db.rollback()
                logger.info(f"Skipping already-processed order {order_id} ({token_id})")
                return

            # Release the full reservation and deduct only what was actually spent.
            # For buys: if execution_price < limit price the difference is returned to available.
            surplus = reserved_amount - actual_spent  # > 0 on buy price improvement; 0 for sells
            balance_cursor = await db.execute(
                """UPDATE balances
                   SET reserved  = reserved  - ?,
                       total     = total     - ?,
                       available = available + ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ? AND asset = ?
                     AND reserved >= ?
                     AND total >= ?""",
                (reserved_amount, actual_spent, surplus, user_id, spent_asset, reserved_amount, actual_spent)
            )

            if balance_cursor.rowcount == 0:
                await db.rollback()
                raise ValueError(
                    f"Inconsistent {spent_asset} balance while executing order {token_id}"
                )
            
            cursor = await db.execute(
                "SELECT id FROM balances WHERE user_id = ? AND asset = ?",
                (user_id, received_asset)
            )
            if await cursor.fetchone():
                await db.execute(
                    """UPDATE balances
                       SET total = total + ?,
                           available = available + ?,
                           updated_at = CURRENT_TIMESTAMP
                       WHERE user_id = ? AND asset = ?""",
                    (received_amount, received_amount, user_id, received_asset)
                )
            else:
                await db.execute(
                    """INSERT INTO balances (user_id, asset, total, available, reserved)
                       VALUES (?, ?, ?, ?, 0)""",
                    (user_id, received_asset, received_amount, received_amount)
                )
            
            await db.commit()
            
            self.orders_executed += 1
            logger.info(
                f"Executed order {order_id}: {side.upper()} {quantity} {symbol} "
                f"@ {execution_price:.2f} (limit: {price:.2f})"
            )
            
            # Send WebSocket update to user
            if self.websocket_manager:
                order_data = {
                    "id": order_id,
                    "token_id": token_id,
                    "symbol": symbol,
                    "side": side,
                    "price": price,
                    "quantity": quantity,
                    "filled_quantity": quantity,
                    "status": "filled",
                    "execution_price": execution_price
                }
                await self.websocket_manager.send_order_update(user_id, order_data)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to execute order {order_id}: {e}", exc_info=True)
            raise
    
    def get_stats(self) -> dict:
        """Get current stats of the execution engine"""
        return {
            "running": self.running,
            "orders_executed": self.orders_executed,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "check_interval": self.check_interval
        }
