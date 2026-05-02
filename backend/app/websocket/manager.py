"""WebSocket 连接池。

支持同一账号多端在线（多 Tab、移动端 + 桌面端等），
所以 user_id → set[WebSocket]，而不是 1:1。

注意：本类是进程内单例。多进程部署时需要换成 Redis pub/sub 做跨进程广播
（Phase 2/3 上线时再处理，1.2b 单进程够用）。
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._conns: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        """添加一个已 accept() 的连接。"""
        async with self._lock:
            self._conns[user_id].add(ws)
        logger.info("ws connect: user_id=%s, total_conns=%d", user_id, self.online_count())

    async def disconnect(self, user_id: int, ws: WebSocket) -> None:
        """移除一个连接。允许重复调用（连接已不在时静默返回）。"""
        async with self._lock:
            conns = self._conns.get(user_id)
            if not conns:
                return
            conns.discard(ws)
            if not conns:
                self._conns.pop(user_id, None)
        logger.info(
            "ws disconnect: user_id=%s, total_conns=%d", user_id, self.online_count()
        )

    async def send_to_user(self, user_id: int, payload: dict) -> int:
        """推送 JSON payload 给指定用户的所有连接。

        返回成功送达的连接数。某个连接失败不影响其他连接（失败的会从池里移除）。
        """
        # 复制一份避免迭代时被改
        async with self._lock:
            conns = list(self._conns.get(user_id, ()))

        if not conns:
            return 0

        delivered = 0
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(payload)
                delivered += 1
            except Exception as e:
                logger.warning("ws send failed for user_id=%s: %s", user_id, e)
                dead.append(ws)

        # 清理发送失败的连接（一般是已断开但还没触发 disconnect）
        if dead:
            async with self._lock:
                conns_set = self._conns.get(user_id)
                if conns_set:
                    for ws in dead:
                        conns_set.discard(ws)
                    if not conns_set:
                        self._conns.pop(user_id, None)

        return delivered



    def online_count(self) -> int:
        """当前活动连接总数（不是用户数）。"""
        return sum(len(s) for s in self._conns.values())


# 进程内单例
manager = ConnectionManager()
