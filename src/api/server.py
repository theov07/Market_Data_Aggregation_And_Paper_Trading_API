"""
FastAPI server for Market Data Aggregation API
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.services.websocket_manager import WebSocketManager
from src.api.services.market_data_service import MarketDataService
from src.api.routes import info, websocket, ws_docs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# Global instances
websocket_manager = WebSocketManager()
market_data_service = MarketDataService(websocket_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    await _startup()
    yield
    # Shutdown
    await _shutdown()


async def _startup():
    """Start market data service on application startup"""
    print("🚀 Starting Market Data Aggregation API...")
    await market_data_service.start()
    print("✅ Market data service started")
    print(f"📊 Monitoring symbols: {', '.join(market_data_service.get_available_symbols())}")
    print(f"🔄 Exchanges: {', '.join(market_data_service.get_available_exchanges())}")


async def _shutdown():
    """Stop market data service on application shutdown"""
    print("🛑 Stopping Market Data Aggregation API...")
    await market_data_service.stop()
    print("✅ Market data service stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
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
    """Add middleware to application"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _include_routers(app: FastAPI):
    """Include API routers"""
    app.include_router(info.router, tags=["Info"])
    app.include_router(ws_docs.router, tags=["WebSocket"])
    app.include_router(websocket.router, tags=["WebSocket"])


def _add_root_endpoint(app: FastAPI):
    """Add root endpoint"""
    @app.get(
        "/",
        summary="API Root",
        description="Root endpoint providing API information and available endpoints",
        tags=["Root"],
        responses={
            200: {
                "description": "API information",
                "content": {
                    "application/json": {
                        "example": {
                            "message": "Market Data Aggregation API",
                            "version": "1.0.0",
                            "description": "Real-time cryptocurrency market data aggregation",
                            "endpoints": {
                                "info": "/info",
                                "websocket": "/ws",
                                "docs": "/docs",
                                "openapi": "/openapi.json"
                            },
                            "websocket_data_types": ["best_touch", "trade", "kline", "ewma"],
                            "status": "operational"
                        }
                    }
                }
            }
        }
    )
    async def root():
        return {
            "message": "Market Data Aggregation API",
            "version": "1.0.0",
            "description": "Real-time cryptocurrency market data aggregation from multiple exchanges",
            "endpoints": {
                "info": "/info",
                "websocket": "/ws",
                "docs": "/docs",
                "openapi": "/openapi.json"
            },
            "websocket_data_types": ["best_touch", "trade", "kline", "ewma"],
            "status": "operational"
        }


# Create application instance
app = create_app()
