# PowerChat 开发进度

> 本文档记录每个里程碑完成的内容、当前能力、明天的起点。

---

## 总进度概览

```
✅ 1.1  后端骨架（注册/登录/JWT）            [已完成 + 已 push]
✅ 1.2a 好友关系 REST                        [已完成]
✅ 1.2b WebSocket 私聊                       [已完成 - 待 commit]
🔜 1.3  前端接入（Vue 项目 + 登录页 + 聊天页）[下一步]
```

---

## ✅ 里程碑 1.1：后端骨架（已完成）

### 完成的工作

| 类别 | 内容 |
|---|---|
| **环境** | Docker Compose 起 MySQL 8 + Redis 7（`docker-compose.dev.yml`） |
| **依赖** | conda 环境 `ecommerce-agent`，依赖见 `backend/requirements.txt` |
| **配置** | `.env` 集中管理 DB/Redis/JWT 配置；`pydantic-settings` 加载 |
| **数据库** | Alembic 接入 async SQLAlchemy；users 表迁移已生成并执行 |
| **API 分层** | `api/` (路由) → `services/` (业务) → `models/` (ORM) + `schemas/` (Pydantic) + `core/` (security/dep) |
| **认证** | bcrypt 密码哈希 + JWT (HS256) access token |
| **接口** | `POST /auth/register`、`POST /auth/login`、`GET /users/me`、`GET /health` |
| **Git** | 独立仓库 `git@github.com:zwygobest/PowerChat.git`，1.1 已 push 到 main |

### 当前可用接口

| Method | Path | 说明 | 鉴权 |
|---|---|---|---|
| GET | `/health` | 健康检查（含 mysql/redis 探活） | ❌ |
| POST | `/api/v1/auth/register` | 注册（成功返回 token + user） | ❌ |
| POST | `/api/v1/auth/login` | 登录 | ❌ |
| GET | `/api/v1/users/me` | 当前用户信息 | ✅ Bearer Token |

Swagger 文档：`http://localhost:8000/docs`

### 当前数据库状态
- 表：`users`（id, username, nickname, password_hash, avatar_url, bio, is_active, created_at, updated_at）
- Alembic 版本：`f911b714f2cd` (create users table)
- 测试数据：1 个用户 `yuan` / `Yuan` / 密码 `123456`

---

## ✅ 里程碑 1.2a：好友关系 REST（已完成）

### 完成的工作

| 类别 | 内容 |
|---|---|
| **数据模型** | `Friendship` ORM + `FriendshipStatus` 枚举（`pending` / `accepted` / `rejected`，暂不含 `blocked`） |
| **迁移** | `089035e503b4_create_friendships_table.py`，已 upgrade |
| **业务规则** | service 层统一处理：不能加自己 / 用户不存在 / 已是好友 / 同方向 pending / 反方向 pending / 同方向 rejected 复用记录改回 pending |
| **接口** | 3 个 REST 路由，全部 JWT 鉴权 |
| **测试** | 4 个核心场景 + 5 个边界场景 + 2 个进阶分支 全部通过 |

### 当前可用接口（1.2a 新增）

| Method | Path | 说明 | 鉴权 |
|---|---|---|---|
| GET | `/api/v1/friends` | 列出当前用户的好友（双方向 join） | ✅ |
| POST | `/api/v1/friends/request` | 发送好友申请（body: `{receiver_id}`） | ✅ |
| PUT | `/api/v1/friends/request/{id}` | 同意/拒绝（body: `{action: accept\|reject}`） | ✅ |

### 关键设计取舍

1. **status 暂不含 `blocked`** — 留到后期真正做拉黑功能时再加迁移
2. **rejected 记录保留** — 便于复用：同方向再申请时改回 pending（避免触发唯一约束）
3. **入参只支持 `receiver_id`** — 用户名搜索是另一个独立功能（Phase 3）
4. **复合唯一约束 + service 层反方向检查** — 数据库防同方向重复，业务层防反方向并发

### 当前数据库状态（更新）
- 新增表：`friendships`（id, requester_id, receiver_id, status, created_at, updated_at；唯一约束 `uq_friendship_pair(requester_id, receiver_id)`）
- Alembic 版本：`089035e503b4` (create friendships table)
- 测试数据：3 个用户 `yuan(1)` / `alice(2)` / `Gretta(3)`，密码均 `123456`
- friendships 表数据：
  - `id=1  yuan→Gretta   accepted`
  - `id=2  Gretta→alice  pending`

---

## ✅ 里程碑 1.2b：WebSocket 私聊（已完成）

### 完成的工作

| 类别 | 内容 |
|---|---|
| **数据模型** | `Message` ORM + `MessageType` 枚举（`text` / `image` / `file` / `audio` / `system`，1.2b 只用 text） |
| **迁移** | `f0c033a21392_create_messages_table.py`，已 upgrade。索引：`idx_msg_sender_receiver` / `idx_msg_receiver_sender` 两个复合索引覆盖双向查询 |
| **业务层** | `message_service`：`is_friend` / `save_private_message`（校验：sender≠receiver → receiver 存在且 active → 是好友 → 落库）/ `list_private_history`（双向 OR + id DESC 游标分页 + limit cap 100）|
| **WebSocket 子系统** | `app/websocket/` 四个文件：`events.py`（事件 / 错误码常量）、`manager.py`（`ConnectionManager` 进程内单例，`dict[int, set[WebSocket]]` 支持多端登录）、`auth.py`（query token 鉴权，5 道防线，失败用 close code 4401）、`handler.py`（accept → 鉴权 → 注册 → 消息循环 → 分发 → 清理）|
| **REST 历史** | `GET /api/v1/messages/private/{user_id}?limit=50&before_id=...`，复用同一个 `list_private_history` |
| **路由注册** | `main.py` 加 `@app.websocket("/ws")`，`api/v1/router.py` 注册 messages |
| **联调** | `scripts/ws_test_client.py` 端到端跑通：双方登录 → 连 WS → 双向发消息 → 各自收 ack/new_message → 拉历史断言通过 |

### 关键设计取舍

1. **消息表只加复合索引** — `idx_msg_sender_receiver` 和 `idx_msg_receiver_sender`，两个 `and_` 分别命中两个索引；不加单列冗余索引（最左前缀已覆盖）
2. **`receiver_id` NOT NULL，先不加 `group_id`** — 1.2b 只做私聊，群聊那次迁移再改 nullable 并加 `group_id`（YAGNI）
3. **`is_recalled` 提前加** — 撤回功能 Phase 2 才做，但 bool 字段成本极低，预留避免后期迁移
4. **多端登录用 `set[WebSocket]`** — 同账号 Chrome + 手机 + 多 Tab 都能收，ack 也广播给发送方所有端实现"多端同步"
5. **业务错误转 error payload，不断连** — service 层 `HTTPException` 在 handler 里 catch 后转 `{type: error, code, detail}`；只有鉴权失败、协议错误、handler 崩了才 close
6. **离线消息只入库不补推** — 接收方上线靠 REST 拉历史；不做"上线一次性补推队列"，简单可靠
7. **每条入站消息开新 DB session** — 长连接全程不持有 session，避免长事务把连接池占死
8. **锁内拿快照，锁外做 I/O** — `send_to_user` 在锁内复制 set，循环发送在锁外，发送失败的连接事后再加锁清理；锁持有时间从 ms 降到 μs

### 当前可用接口（1.2b 新增）

| Method | Path | 说明 | 鉴权 |
|---|---|---|---|
| WS | `/ws?token=<jwt>` | WebSocket 长连接 | ✅ query token |
| GET | `/api/v1/messages/private/{user_id}?limit=50&before_id=...` | 私聊历史（id DESC + 游标分页） | ✅ Bearer |

WebSocket 事件协议（payload 都是 JSON）：

| 方向 | type | 字段 | 说明 |
|---|---|---|---|
| C→S | `private_message` | `receiver_id`, `content`, `msg_type?` | 发私聊 |
| C→S | `ping` | — | 心跳 |
| S→C | `new_message` | `message: MessageOut` | 推给接收方 |
| S→C | `message_ack` | `message: MessageOut` | 回给发送方所有端（多端同步）|
| S→C | `error` | `code`, `detail` | 业务错误（不断连）|
| S→C | `system` | `detail` | 系统通知（如欢迎包）|
| S→C | `pong` | — | 心跳回包 |

错误码：`invalid_payload` / `unknown_event` / `not_friend` / `receiver_not_found` / `self_message` / `internal_error`。

### 当前数据库状态（更新）

- 新增表：`messages`（id, sender_id, receiver_id, msg_type, content, file_name, file_size, is_recalled, created_at；2 个复合索引）
- Alembic 版本：`f0c033a21392` (create messages table)
- 测试数据：联调脚本跑过后，messages 表里有 yuan ↔ Gretta 的 2 条对话记录

### 已知未做的尾巴（不影响 1.2b 验收）

- ❌ 不是好友的 receiver、错 token 这些边界场景没写进自动化测试，靠 Swagger / `wscat` 手动验证
- ❌ 多进程部署需要 Redis pub/sub 跨 worker 广播（manager.py 注释里有提示）
- ❌ 心跳 ping/pong 服务端没主动断不活动连接（客户端可发 ping，服务端可 pong；后续可加超时主动 close）
- ❌ 离线消息"上线一次性补推"（按规划放到 Phase 2）

---

## 项目当前结构

```
PowerChat/
├── PROGRESS.md                       ← 本文档
├── PowerChat_ProjectPlan.md          ← 总体规划
├── docker-compose.dev.yml            ← MySQL + Redis 编排
├── .gitignore / .env.example
└── backend/
    ├── .env                          ← 本地配置（不入 git）
    ├── requirements.txt
    ├── alembic.ini
    ├── alembic/
    │   ├── env.py                    ← 已配置 async + 自动读 .env
    │   └── versions/
    │       ├── f911b714f2cd_create_users_table.py
    │       ├── 089035e503b4_create_friendships_table.py    ← 1.2a
    │       └── f0c033a21392_create_messages_table.py        ← 1.2b
    ├── scripts/
    │   └── ws_test_client.py         ← 1.2b 端到端联调脚本
    └── app/
        ├── main.py                   ← FastAPI 入口（含 /ws 路由）
        ├── config.py                 ← Settings (.env)
        ├── database.py               ← async engine + Base + get_db
        ├── redis_client.py
        ├── models/{user,friendship,message}.py
        ├── schemas/{user,auth,friendship,message}.py
        ├── services/{auth_service,friend_service,message_service}.py
        ├── core/{security,dependencies}.py
        ├── api/v1/{router,auth,users,friends,messages}.py
        └── websocket/                 ← 1.2b 新增
            ├── events.py              ← 事件 / 错误码常量
            ├── manager.py             ← ConnectionManager 连接池
            ├── auth.py                ← WS 鉴权
            └── handler.py             ← 消息分发主循环
```

---

## 明天怎么继续：开发环境恢复 Checklist

按顺序执行，每步通过再下一步：

```bash
# 1. 进项目目录
cd /Users/weiyuanzheng/Desktop/学习日常/vibe-coding/PowerChat

# 2. 起容器（昨天关机后会停止，启动它们）
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml ps
# 期望：mysql 和 redis 都 Up

# 3. 激活 conda 环境
conda activate ecommerce-agent

# 4. 启动后端
cd backend
uvicorn app.main:app --reload --port 8000

# 5. 另开终端，确认健康
curl http://localhost:8000/health
# 期望：{"status":"ok","mysql":"ok","redis":"ok"}

# 6. 确认登录依然能拿到 token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"yuan","password":"123456"}'
# 期望：返回 access_token
```

如果第 5/6 步失败 → 先看 uvicorn 终端的报错日志再排查。

---

## 🔜 里程碑 1.3：前端接入（下一步）

待做：

- [ ] 新建 Vue 3 项目（Vite + TypeScript + Pinia + Vue Router）
- [ ] 登录页：调 `POST /api/v1/auth/login`，token 存 localStorage
- [ ] 好友列表页：`GET /api/v1/friends`
- [ ] 聊天页：连 `/ws?token=xxx`，发 `private_message` / 收 `new_message` + `message_ack`
- [ ] 进入会话时调 `GET /api/v1/messages/private/{user_id}` 拉历史
- [ ] 断线自动重连 + 心跳

**学习点**：Vue 3 组合式 API、Pinia 状态管理、原生 WebSocket API、TypeScript 类型对齐后端 schema。

**测试基线**：1.2b 的后端能力齐全，可直接用浏览器模拟两端登录，验证端到端体验。

---

## 常用命令速查

### Docker
```bash
docker compose -f docker-compose.dev.yml up -d        # 启动
docker compose -f docker-compose.dev.yml ps           # 查看状态
docker compose -f docker-compose.dev.yml logs mysql   # 看日志
docker compose -f docker-compose.dev.yml stop         # 停止（保留数据）
```

### 数据库
```bash
# 进 MySQL
docker exec -it powerchat_mysql mysql -upowerchat -ppowerchat123 powerchat

# 一次性查询
docker exec -it powerchat_mysql mysql -upowerchat -ppowerchat123 powerchat -e "SELECT * FROM users;"

# 进 Redis
docker exec -it powerchat_redis redis-cli
```

### Alembic（在 backend/ 目录执行）
```bash
alembic revision --autogenerate -m "xxx"   # 生成迁移
alembic upgrade head                       # 应用到最新
alembic downgrade -1                       # 回滚一版
alembic current                            # 当前版本
alembic history                            # 历史
```

### Git
```bash
git status
git add <file>
git commit -m "feat: xxx"
git push                                   # 已配 -u origin main，省参数
```

---

## 待办的小尾巴（不紧急）

- [ ] 把外层 vibe-coding 仓库的 .gitignore 加上 `PowerChat/`，避免它继续追踪 PowerChat 改动
- [ ] 1.1 的 Refresh Token 机制（目前只有 access token，60 分钟过期就要重新登录）—— 后期补
