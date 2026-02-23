import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.services.websocket_manager import WebSocketManager
from src.api.services.market_data_service import MarketDataService
from src.api.services.auth_service import AuthService
from src.api.services.trading_service import TradingService
from src.api.services.order_execution_engine import OrderExecutionEngine
from src.api.routes import info, websocket, ws_docs, auth, trading
from src.api import dependencies

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# Global instances
websocket_manager = WebSocketManager()
market_data_service = MarketDataService(websocket_manager)
auth_service = AuthService()
trading_service = None  # Will be initialized after market_data_service starts
execution_engine = None  # Will be initialized after market_data_service starts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan"""
    await _startup()
    yield
    await _shutdown()


async def _startup():
    """startup"""
    global execution_engine, trading_service
    
    print("Starting Market Data Aggregation API...")
    
    await auth_service.init_db()
    print("Authentication database initialized")
    
    # Set services for routes and dependencies
    auth.auth_service = auth_service
    dependencies.set_auth_service(auth_service)
    
    await market_data_service.start()
    print("Market data service started")
    print(f"Monitoring symbols: {', '.join(market_data_service.get_available_symbols())}")
    print(f"Exchanges: {', '.join(market_data_service.get_available_exchanges())}")
    
    # Initialize trading service with best_touch_aggregator for market orders
    trading_service = TradingService(best_touch_aggregator=market_data_service.best_touch_aggregator)
    await trading_service.init_db()
    print("Trading database initialized")
    
    # Set trading service for routes
    trading.trading_service = trading_service
    
    execution_engine = OrderExecutionEngine(
        best_touch_aggregator=market_data_service.best_touch_aggregator,
        websocket_manager=websocket_manager
    )
    await execution_engine.start()
    print("Order execution engine started")


async def _shutdown():
    """shutdown"""
    print("Stopping Market Data Aggregation API...")
    
    if execution_engine:
        await execution_engine.stop()
    
    await market_data_service.stop()
    print("Market data service stopped")


def create_app() -> FastAPI:
    """Create app"""
    app = FastAPI(
        title="Market Data Aggregation API",
        description="Real-time cryptocurrency market data aggregation from multiple exchanges",
        version="1.0.0",
        lifespan=lifespan
    )
    
    _add_middleware(app)
    _include_routers(app)
    _add_root_endpoint(app)
    
    return app


def _add_middleware(app: FastAPI):
    """add middleware"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _include_routers(app: FastAPI):
    """include routers"""
    app.include_router(auth.router)
    app.include_router(trading.router)
    app.include_router(info.router, tags=["Info"])
    app.include_router(ws_docs.router, tags=["WebSocket"])
    app.include_router(websocket.router, tags=["WebSocket"])


def _add_root_endpoint(app: FastAPI):
    """add root endpoint"""
    @app.get("/", tags=["Root"])
    async def root():
        """Root"""
        return {
            "message": "Market Data Aggregation API",
            "version": "1.0.0",
            "description": "Real-time cryptocurrency market data aggregation from multiple exchanges",
            "endpoints": {
                "register": "/auth/register",
                "login": "/auth/login",
                "info": "/info",
                "deposit": "/deposit",
                "balance": "/balance",
                "orders": "/orders",
                "websocket": "/ws",
                "docs": "/docs",
                "openapi": "/openapi.json"
            },
            "websocket_data_types": ["best_touch", "trade", "kline", "ewma"],
            "status": "operational"
        }


app = create_app()
