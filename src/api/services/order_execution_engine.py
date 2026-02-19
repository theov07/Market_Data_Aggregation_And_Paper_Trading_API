import asyncio
import logging
from datetime import datetime
from typing import Optional
import aiosqlite

from src.api.models.trading_models import OrderResponse
from src.processors.best_touch import BestTouchAggregator

logger = logging.getLogger(__name__)

DB_PATH = "users.db"


class OrderExecutionEngine:
    
    def __init__(
        self, 
        best_touch_aggregator: BestTouchAggregator,
        db_path: str = DB_PATH,
        check_interval: float = 0.5
    ):
        self.best_touch_aggregator = best_touch_aggregator
        self.db_path = db_path
        self.check_interval = check_interval
        
        self.running = False
        self._task: Optional[asyncio.Task] = None
        
        self.orders_executed = 0
        self.last_check_time: Optional[datetime] = None
    
    async def start(self):
        """Start the order execution engine"""
        if self.running:
            logger.warning("Execution engine already running")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._execution_loop())
        logger.info("Order execution engine started")
    
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
        
        logger.info(f"Order execution engine stopped (executed {self.orders_executed} orders)")
    
    async def _execution_loop(self):
        """Main loop to check and execute orders"""
        logger.info("Execution loop started")
        
        while self.running:
            try:
                await self._check_and_execute_orders()
                self.last_check_time = datetime.now()
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
                    await self._try_execute_order(db, order)
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
                spent_amount = price * quantity
                received_asset = base_asset
                received_amount = quantity
                
            else:
                spent_asset = base_asset
                spent_amount = quantity
                received_asset = quote_asset
                received_amount = execution_price * quantity
            
            await db.execute(
                """UPDATE orders 
                   SET status = 'filled', executed_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (order_id,)
            )
            
            await db.execute(
                """UPDATE balances
                   SET reserved = reserved - ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ? AND asset = ?""",
                (spent_amount, user_id, spent_asset)
            )
            
            await db.execute(
                """UPDATE balances
                   SET total = total - ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ? AND asset = ?""",
                (spent_amount, user_id, spent_asset)
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
