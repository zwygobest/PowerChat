# PowerChat 开发进度

> 本文档记录每个里程碑完成的内容、当前能力、明天的起点。

---

## 总进度概览

```
✅ 1.1  后端骨架（注册/登录/JWT）            [已完成 + 已 push]
✅ 1.2a 好友关系 REST                        [已完成 - 待 commit]
🔜 1.2b WebSocket 私聊                       [下一步]
   1.3  前端接入（Vue 项目 + 登录页 + 聊天页）
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
    │       └── 089035e503b4_create_friendships_table.py    ← 1.2a
    └── app/
        ├── main.py                   ← FastAPI 入口
        ├── config.py                 ← Settings (.env)
        ├── database.py               ← async engine + Base + get_db
        ├── redis_client.py
        ├── models/{user,friendship}.py
        ├── schemas/{user,auth,friendship}.py
        ├── services/{auth_service,friend_service}.py
        ├── core/{security,dependencies}.py
        └── api/v1/{router,auth,users,friends}.py
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

## 🔜 里程碑 1.2b：WebSocket 私聊（下一步）

待做：

- [ ] 新建 Message 模型（`app/models/message.py`）+ 迁移
- [ ] `app/websocket/manager.py`：`ConnectionManager` 连接池
- [ ] `app/websocket/handler.py`：消息分发逻辑
- [ ] `app/websocket/events.py`：消息类型常量
- [ ] `main.py` 注册 `/ws` 路由 + JWT 鉴权（从 query string 取 token）
- [ ] `services/message_service.py`：消息持久化、查询历史
- [ ] `api/v1/messages.py`：`GET /messages/private/{user_id}` 查历史
- [ ] 用 `wscat` 模拟两个用户实时聊天

**学习点**：WebSocket 协议、长连接鉴权、广播 vs 点对点、消息持久化时机。

**测试基线**：1.2a 的三个用户已具备好友关系（yuan ↔ Gretta），可直接用来测私聊；alice 暂时是孤岛。

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

- [ ] `ssh-add --apple-use-keychain ~/.ssh/id_ed25519` 让 SSH 不再问 passphrase
- [ ] 把外层 vibe-coding 仓库的 .gitignore 加上 `PowerChat/`，避免它继续追踪 PowerChat 改动
- [ ] 1.1 的 Refresh Token 机制（目前只有 access token，60 分钟过期就要重新登录）—— 后期补
