"""
Start the FastAPI server
"""
import uvicorn


def start_server():
    """Start the FastAPI server with uvicorn"""
    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    start_server()
