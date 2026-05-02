"""WebSocket 联调测试脚本（手动跑，不是 pytest）。

用法：
    # 1. 启动后端：
    #    uvicorn app.main:app --reload --port 8000
    # 2. 跑这个脚本：
    cd backend && python -m scripts.ws_test_client

预期效果：
    - yuan 和 Gretta 各自登录拿到 token
    - 两人各自连上 /ws
    - yuan 发一条消息 → Gretta 收到（new_message）+ yuan 收到 ack（message_ack）
    - Gretta 回一条 → yuan 收到（new_message）+ Gretta 收到 ack（message_ack）
    - 双方各自 GET /api/v1/messages/private/{对方id} 拉历史 → 应能看到刚发的消息

依赖前提（在 docker 里已经准备好）：
    yuan(1) / Gretta(3) 互为好友（accepted），密码均 123456。
"""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from urllib.parse import quote

import httpx
import websockets

HTTP_BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


async def login(client: httpx.AsyncClient, username: str, password: str) -> tuple[str, int]:
    """登录返回 (token, user_id)。"""
    r = await client.post(
        f"{HTTP_BASE}/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    r.raise_for_status()
    data = r.json()
    return data["access_token"], data["user"]["id"]


async def fetch_history(client: httpx.AsyncClient, token: str, other_id: int) -> list[dict]:
    r = await client.get(
        f"{HTTP_BASE}/api/v1/messages/private/{other_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# WS 客户端封装
# ---------------------------------------------------------------------------


class WsClient:
    """简易 WS 客户端：连接 + 后台收消息打印。"""

    def __init__(self, name: str, token: str, user_id: int):
        self.name = name
        self.token = token
        self.user_id = user_id
        self.ws: websockets.ClientConnection | None = None
        self._reader_task: asyncio.Task | None = None
        self.received: list[dict] = []

    async def connect(self) -> None:
        url = f"{WS_BASE}/ws?token={quote(self.token)}"
        self.ws = await websockets.connect(url)
        self._reader_task = asyncio.create_task(self._reader())
        print(f"[{self.name}] connected as user_id={self.user_id}")

    async def _reader(self) -> None:
        assert self.ws is not None
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                self.received.append(msg)
                print(f"[{self.name}] ⇐ {msg}")
        except websockets.ConnectionClosed:
            print(f"[{self.name}] connection closed")

    async def send_private(self, receiver_id: int, content: str) -> None:
        assert self.ws is not None
        payload = {
            "type": "private_message",
            "receiver_id": receiver_id,
            "content": content,
        }
        print(f"[{self.name}] ⇒ {payload}")
        await self.ws.send(json.dumps(payload))

    async def close(self) -> None:
        if self.ws is not None:
            await self.ws.close()
        if self._reader_task is not None:
            with suppress(Exception):
                await self._reader_task


# ---------------------------------------------------------------------------
# 主测试流程
# ---------------------------------------------------------------------------


async def main() -> None:
    async with httpx.AsyncClient(timeout=5.0) as http:
        print("=== 1) 登录 ===")
        yuan_token, yuan_id = await login(http, "yuan", "123456")
        gretta_token, gretta_id = await login(http, "Gretta", "123456")
        print(f"yuan id={yuan_id}, Gretta id={gretta_id}")

        print("\n=== 2) 连接 WS ===")
        yuan = WsClient("yuan", yuan_token, yuan_id)
        gretta = WsClient("Gretta", gretta_token, gretta_id)
        await yuan.connect()
        await gretta.connect()

        # 等服务器把 system 欢迎包发完
        await asyncio.sleep(0.3)

        print("\n=== 3) yuan → Gretta ===")
        await yuan.send_private(gretta_id, "你好 Gretta，今晚一起吃饭？")
        await asyncio.sleep(0.5)

        print("\n=== 4) Gretta → yuan ===")
        await gretta.send_private(yuan_id, "好啊，七点见。")
        await asyncio.sleep(0.5)

        print("\n=== 5) 关闭 WS ===")
        await yuan.close()
        await gretta.close()

        print("\n=== 6) 拉历史（REST）===")
        yuan_history = await fetch_history(http, yuan_token, gretta_id)
        gretta_history = await fetch_history(http, gretta_token, yuan_id)
        print(f"yuan 看到的历史（{len(yuan_history)} 条）:")
        for m in yuan_history:
            print(f"  id={m['id']} {m['sender_id']}->{m['receiver_id']} {m['content']!r}")
        print(f"Gretta 看到的历史（{len(gretta_history)} 条）:")
        for m in gretta_history:
            print(f"  id={m['id']} {m['sender_id']}->{m['receiver_id']} {m['content']!r}")

        # 简单断言
        assert len(yuan_history) >= 2, "yuan 应该能看到至少 2 条消息"
        assert len(gretta_history) >= 2, "Gretta 应该能看到至少 2 条消息"
        print("\n✅ 测试通过")


if __name__ == "__main__":
    asyncio.run(main())
