"""WebSocket 鉴权辅助。

浏览器原生 WebSocket API 不能加自定义 header，所以 token 走 query string：
    ws://host/ws?token=<jwt>

校验通过返回 User；失败关闭连接并返回 None（用 4401 自定义关闭码，
1xxx 是协议保留段，4xxx 是应用自定义段）。
"""

from __future__ import annotations

from fastapi import WebSocket, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.models.user import User


WS_CLOSE_UNAUTHORIZED = 4401  # 自定义：鉴权失败
WS_CLOSE_POLICY_VIOLATION = status.WS_1008_POLICY_VIOLATION


async def authenticate_ws(websocket: WebSocket, db: AsyncSession) -> User | None:
    """从 query string 取 token，解码、查 User。

    注意：调用前 WS 还没 accept；本函数只负责验证身份，
    accept/close 由调用方决定（通常失败时直接 close，成功后再 accept）。
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="missing token")
        return None

    try:
        payload = decode_access_token(token)
    except JWTError:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="invalid token")
        return None

    sub = payload.get("sub")
    if sub is None:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="invalid token payload")
        return None

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="invalid token payload")
        return None

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="user inactive or not found")
        return None

    return user
