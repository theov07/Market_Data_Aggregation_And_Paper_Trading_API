"""
Start the FastAPI server
"""
import uvicorn
from config import API_HOST, API_PORT


def start_server():
    uvicorn.run(
        "src.api.server:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    start_server()
