from fastapi import FastAPI, WebSocket
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import settings
from app.database import engine
from app.redis_client import redis_client
from app.websocket.handler import ws_endpoint

app = FastAPI(title="PowerChat API", debug=settings.DEBUG)
app.include_router(api_router)


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket) -> None:
    await ws_endpoint(websocket)


@app.get("/health")
async def health():
    result = {"status": "ok", "mysql": "unknown", "redis": "unknown"}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        result["mysql"] = "ok"
    except Exception as e:
        result["mysql"] = f"error: {e.__class__.__name__}"
        result["status"] = "degraded"

    try:
        pong = await redis_client.ping()
        result["redis"] = "ok" if pong else "no_pong"
    except Exception as e:
        result["redis"] = f"error: {e.__class__.__name__}"
        result["status"] = "degraded"

    return result
