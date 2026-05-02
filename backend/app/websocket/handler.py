"""WebSocket 消息分发主循环。

流程：
    accept → 鉴权（query token） → 注册到 ConnectionManager
    while True:
        收到 JSON → 按 type 分发 → 业务处理（存库 + 推送 + ack）
        业务错误 → 回 error payload，不断连
    断开 → 从 ConnectionManager 注销

注意会话管理：长连接全程不持有一个 DB session，
而是每条入站消息开一个新 session（避免长事务）。
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user import User
from app.schemas.message import MessageOut, PrivateMessageIn
from app.services.message_service import save_private_message
from app.websocket import events
from app.websocket.auth import authenticate_ws
from app.websocket.manager import manager

logger = logging.getLogger(__name__)


async def _send_error(ws: WebSocket, code: str, detail: str) -> None:
    """业务错误：回 error payload，连接保持不变。"""
    try:
        await ws.send_json(
            {"type": events.EVT_ERROR, "code": code, "detail": detail}
        )
    except Exception as e:
        logger.warning("failed to send error payload: %s", e)


def _http_exc_to_code(exc: HTTPException) -> str:
    """把 service 层的 HTTPException 映射成 WS 错误码。"""
    detail = (exc.detail or "").lower()
    if "yourself" in detail:
        return events.ERR_SELF_MESSAGE
    if "receiver not found" in detail:
        return events.ERR_RECEIVER_NOT_FOUND
    if "not friends" in detail:
        return events.ERR_NOT_FRIEND
    return events.ERR_INTERNAL


async def _handle_private_message(
    ws: WebSocket, sender: User, db: AsyncSession, payload: dict
) -> None:
    try:
        data = PrivateMessageIn.model_validate(payload)
    except ValidationError as e:
        await _send_error(ws, events.ERR_INVALID_PAYLOAD, e.errors()[0]["msg"])
        return

    try:
        msg = await save_private_message(
            db,
            sender_id=sender.id,
            receiver_id=data.receiver_id,
            content=data.content,
            msg_type=data.msg_type,
        )
    except HTTPException as e:
        await _send_error(ws, _http_exc_to_code(e), str(e.detail))
        return

    msg_payload = MessageOut.model_validate(msg).model_dump(mode="json")

    # 给发送方 ack（包括其它端的多 Tab 同步）
    await manager.send_to_user(
        sender.id, {"type": events.EVT_MESSAGE_ACK, "message": msg_payload}
    )

    # 给接收方推送（不在线时静默：消息已入库，对方上线拉历史能看到）
    await manager.send_to_user(
        data.receiver_id, {"type": events.EVT_NEW_MESSAGE, "message": msg_payload}
    )


async def ws_endpoint(websocket: WebSocket) -> None:
    """注册到 FastAPI 路由的入口。"""
    # accept 前先鉴权失败可以拒绝（Starlette 允许 close 在 accept 前调用）
    async with AsyncSessionLocal() as auth_db:
        user = await authenticate_ws(websocket, auth_db)
    if user is None:
        return

    await websocket.accept()
    await manager.connect(user.id, websocket)
    await websocket.send_json(
        {"type": events.EVT_SYSTEM, "detail": f"connected as user_id={user.id}"}
    )

    try:
        while True:
            payload = await websocket.receive_json()
            event_type = payload.get("type") if isinstance(payload, dict) else None

            if event_type == events.EVT_PRIVATE_MESSAGE:
                async with AsyncSessionLocal() as db:
                    await _handle_private_message(websocket, user, db, payload)
            elif event_type == events.EVT_PING:
                await websocket.send_json({"type": events.EVT_PONG})
            else:
                await _send_error(
                    websocket,
                    events.ERR_UNKNOWN_EVENT,
                    f"unknown event type: {event_type!r}",
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("ws handler crashed for user_id=%s: %s", user.id, e)
        try:
            await _send_error(websocket, events.ERR_INTERNAL, "internal error")
        except Exception:
            pass
    finally:
        await manager.disconnect(user.id, websocket)
