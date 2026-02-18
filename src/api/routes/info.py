"""
Info endpoint - provides available assets and exchanges
"""
from fastapi import APIRouter, Depends

from src.api.models.api_models import InfoResponse
from src.api.services.market_data_service import MarketDataService


router = APIRouter()


def get_market_data_service() -> MarketDataService:
    """Dependency to get market data service"""
    from src.api.server import market_data_service
    return market_data_service


@router.get(
    "/info",
    response_model=InfoResponse,
    summary="Get market information",
    description="""
    Returns information about available assets, trading pairs, exchanges and kline intervals.
    
    This endpoint is useful for clients to discover what data is available for subscription
    via WebSocket or for general market information.
    
    **Response includes:**
    - **assets**: List of unique cryptocurrencies (e.g., BTC, ETH, USDT)
    - **trading_pairs**: List of available trading pairs (e.g., BTCUSDT, ETHUSDT)
    - **exchanges**: List of connected exchanges (binance, okx)
    - **kline_intervals**: Available candlestick intervals (1s, 10s, 1m, 5m)
    """,
    response_description="Market information with available assets, pairs, exchanges and intervals",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "assets": ["ADA", "BNB", "BTC", "ETH", "SOL", "USDT"],
                        "trading_pairs": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT"],
                        "exchanges": ["binance", "okx"],
                        "kline_intervals": ["1s", "10s", "1m", "5m"]
                    }
                }
            }
        }
    }
)
async def get_info(service: MarketDataService = Depends(get_market_data_service)) -> InfoResponse:
    """
    Get available assets, trading pairs, exchanges and intervals
    
    Returns:
        InfoResponse with lists of available assets, pairs, exchanges and intervals
    """
    symbols = service.get_available_symbols()
    exchanges = service.get_available_exchanges()
    intervals = service.get_available_intervals()
    
    # Extract unique assets from trading pairs (e.g., BTC, ETH, USDT from BTCUSDT)
    assets = _extract_assets(symbols)
    
    return InfoResponse(
        assets=sorted(assets),
        trading_pairs=symbols,
        exchanges=exchanges,
        kline_intervals=intervals
    )


def _extract_assets(symbols: list[str]) -> list[str]:
    """Extract unique assets from trading pair symbols"""
    assets = set()
    
    for symbol in symbols:
        # Handle USDT pairs (e.g., BTCUSDT -> BTC, USDT)
        if "USDT" in symbol:
            base = symbol.replace("USDT", "")
            assets.add(base)
            assets.add("USDT")
    
    return list(assets)
