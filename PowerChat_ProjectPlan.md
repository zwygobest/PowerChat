# PowerChat 项目规划文档

> 一个类微信的全栈实时聊天应用
> 技术栈：Python FastAPI + WebSocket + MySQL + Redis + Vue 3 + Vite
> 作者：Yuan | 开始日期：2025

---

## 目录

1. [项目简介](#1-项目简介)
2. [系统架构图](#2-系统架构图)
3. [技术栈详情](#3-技术栈详情)
4. [项目文件结构](#4-项目文件结构)
5. [数据库表设计](#5-数据库表设计)
6. [分阶段任务拆解](#6-分阶段任务拆解)
7. [API 接口规范](#7-api-接口规范)
8. [WebSocket 消息协议](#8-websocket-消息协议)
9. [开发规范](#9-开发规范)

---

## 1. 项目简介

**PowerChat** 是一个面向朋友间使用的实时聊天 Web 应用，目标实现微信的核心功能子集，包括：私聊、群聊、文件/图片发送、好友管理、在线状态、朋友圈等。

### 核心目标
- 实现微信核心功能，供朋友小圈子使用
- 全栈练手项目，覆盖后端/实时通信/前端/部署完整链路
- 代码清晰，模块化，便于迭代扩展

### 迭代路线
```
Web 网页版 → Docker 本地部署 → 云服务器上线 → 移动端 App
```

---

## 2. 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端层                               │
│                   Vue 3 + Vite (Web)                         │
│         Pinia状态管理 │ Vue Router │ Axios │ WebSocket       │
└──────────────────────┬──────────────────────────────────────┘
                       │  HTTP REST + WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│                       网关层                                  │
│                  Nginx（反向代理）                             │
│            静态文件托管 │ SSL终止 │ 负载均衡                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                      后端层                                   │
│                 Python FastAPI                               │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  REST API   │  │  WebSocket   │  │   后台任务          │  │
│  │  用户/好友   │  │  实时消息管理  │  │  消息推送/清理      │  │
│  │  群组/文件   │  │  连接池管理   │  │                   │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
└────────────┬──────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────┐
│                      数据层                                   │
│                                                             │
│   ┌─────────────────┐         ┌──────────────────────┐     │
│   │     MySQL        │         │        Redis          │     │
│   │  持久化存储       │         │   缓存 + 会话 + 队列   │     │
│   │  用户/消息/群组   │         │  在线状态 / JWT黑名单  │     │
│   └─────────────────┘         └──────────────────────┘     │
└────────────────────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────┐
│                      存储层                                   │
│           本地文件系统（图片/文件上传）                          │
│           → 后期迁移至 阿里云 OSS                              │
└────────────────────────────────────────────────────────────┘
```

### WebSocket 连接流程
```
客户端登录
    │
    ▼
获取 JWT Token
    │
    ▼
建立 WebSocket 连接  ws://server/ws?token=xxx
    │
    ▼
服务端验证 Token → 注册连接到用户连接池
    │
    ▼
双向实时通信（消息收发、在线状态、已读回执）
    │
    ▼
断开时 → 从连接池移除 → 更新用户离线状态
```

---

## 3. 技术栈详情

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 前端框架 | Vue 3 | 3.x | Composition API |
| 前端构建 | Vite | 5.x | 开发服务器 + 打包 |
| 前端状态 | Pinia | 2.x | 替代 Vuex |
| 前端路由 | Vue Router | 4.x | |
| HTTP 客户端 | Axios | 1.x | 封装请求拦截器 |
| UI 组件库 | Element Plus | 2.x | 快速搭建界面 |
| 后端框架 | FastAPI | 0.110+ | 自动生成 API 文档 |
| 实时通信 | WebSocket | 原生 | FastAPI 内置支持 |
| ORM | SQLAlchemy | 2.x | async 异步版本 |
| 数据迁移 | Alembic | 1.x | 数据库版本管理 |
| 鉴权 | JWT | python-jose | Access + Refresh Token |
| 密码加密 | bcrypt | passlib | |
| 关系型数据库 | MySQL | 8.x | 持久化存储 |
| 缓存数据库 | Redis | 7.x | 会话/状态/队列 |
| 文件存储 | 本地 static/ | - | 后期换 OSS |
| 容器化 | Docker + Compose | - | 部署用 |
| Web 服务器 | Nginx | - | 反向代理 |

---

## 4. 项目文件结构

```
vibe-coding/
└── PowerChat/
    ├── README.md
    ├── docker-compose.yml          # 整体编排
    │
    ├── backend/                    # FastAPI 后端
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── alembic/                # 数据库迁移
    │   │   ├── versions/
    │   │   └── env.py
    │   ├── app/
    │   │   ├── main.py             # 入口，注册路由和中间件
    │   │   ├── config.py           # 环境变量配置
    │   │   ├── database.py         # MySQL 连接
    │   │   ├── redis_client.py     # Redis 连接
    │   │   │
    │   │   ├── models/             # SQLAlchemy ORM 模型
    │   │   │   ├── user.py
    │   │   │   ├── message.py
    │   │   │   ├── group.py
    │   │   │   ├── friendship.py
    │   │   │   └── moment.py       # 朋友圈
    │   │   │
    │   │   ├── schemas/            # Pydantic 请求/响应模型
    │   │   │   ├── user.py
    │   │   │   ├── message.py
    │   │   │   ├── group.py
    │   │   │   └── friendship.py
    │   │   │
    │   │   ├── api/                # REST API 路由
    │   │   │   ├── v1/
    │   │   │   │   ├── auth.py     # 注册/登录/刷新token
    │   │   │   │   ├── users.py    # 用户信息/搜索
    │   │   │   │   ├── friends.py  # 好友增删查
    │   │   │   │   ├── messages.py # 消息历史
    │   │   │   │   ├── groups.py   # 群组管理
    │   │   │   │   ├── files.py    # 文件上传下载
    │   │   │   │   └── moments.py  # 朋友圈
    │   │   │
    │   │   ├── websocket/          # WebSocket 管理
    │   │   │   ├── manager.py      # 连接池管理
    │   │   │   ├── handler.py      # 消息处理逻辑
    │   │   │   └── events.py       # 事件类型定义
    │   │   │
    │   │   ├── services/           # 业务逻辑层
    │   │   │   ├── auth_service.py
    │   │   │   ├── message_service.py
    │   │   │   ├── group_service.py
    │   │   │   └── file_service.py
    │   │   │
    │   │   ├── core/               # 核心工具
    │   │   │   ├── security.py     # JWT 生成/验证
    │   │   │   ├── dependencies.py # FastAPI 依赖注入
    │   │   │   └── exceptions.py   # 全局异常处理
    │   │   │
    │   │   └── static/             # 本地文件存储
    │   │       ├── avatars/
    │   │       └── uploads/
    │
    ├── frontend/                   # Vue 3 + Vite 前端
    │   ├── Dockerfile
    │   ├── package.json
    │   ├── vite.config.js
    │   ├── index.html
    │   └── src/
    │       ├── main.js
    │       ├── App.vue
    │       │
    │       ├── router/
    │       │   └── index.js        # 路由配置
    │       │
    │       ├── stores/             # Pinia 状态
    │       │   ├── auth.js         # 登录状态/token
    │       │   ├── chat.js         # 聊天会话/消息
    │       │   ├── contacts.js     # 好友/群组
    │       │   └── websocket.js    # WS 连接状态
    │       │
    │       ├── api/                # Axios 封装
    │       │   ├── index.js        # axios 实例/拦截器
    │       │   ├── auth.js
    │       │   ├── chat.js
    │       │   └── user.js
    │       │
    │       ├── views/              # 页面级组件
    │       │   ├── LoginView.vue
    │       │   ├── RegisterView.vue
    │       │   └── ChatView.vue    # 主聊天页面（大布局）
    │       │
    │       ├── components/         # 业务组件
    │       │   ├── layout/
    │       │   │   ├── Sidebar.vue         # 左侧导航栏
    │       │   │   ├── ContactList.vue     # 联系人列表
    │       │   │   └── ChatWindow.vue      # 右侧聊天窗口
    │       │   ├── chat/
    │       │   │   ├── MessageBubble.vue   # 消息气泡
    │       │   │   ├── MessageInput.vue    # 输入框
    │       │   │   └── FileUpload.vue      # 文件上传
    │       │   └── common/
    │       │       ├── Avatar.vue
    │       │       └── OnlineStatus.vue
    │       │
    │       └── utils/
    │           ├── websocket.js    # WS 封装
    │           └── time.js         # 时间格式化
    │
    └── nginx/
        └── nginx.conf
```

---

## 5. 数据库表设计

### 5.1 用户表 `users`

```sql
CREATE TABLE users (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    username    VARCHAR(32) UNIQUE NOT NULL,       -- 登录用户名
    nickname    VARCHAR(32) NOT NULL,              -- 显示昵称
    password    VARCHAR(128) NOT NULL,             -- bcrypt 哈希
    avatar_url  VARCHAR(256),                      -- 头像路径
    bio         VARCHAR(128) DEFAULT '',           -- 个人签名
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 5.2 好友关系表 `friendships`

```sql
CREATE TABLE friendships (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    requester_id BIGINT NOT NULL,                  -- 发起方
    receiver_id  BIGINT NOT NULL,                  -- 接收方
    status       ENUM('pending','accepted','blocked') DEFAULT 'pending',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (requester_id) REFERENCES users(id),
    FOREIGN KEY (receiver_id)  REFERENCES users(id),
    UNIQUE KEY uq_friendship (requester_id, receiver_id)
);
```

### 5.3 群组表 `groups`

```sql
CREATE TABLE `groups` (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(64) NOT NULL,
    avatar_url  VARCHAR(256),
    owner_id    BIGINT NOT NULL,                   -- 群主
    description VARCHAR(256) DEFAULT '',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);
```

### 5.4 群组成员表 `group_members`

```sql
CREATE TABLE group_members (
    id         BIGINT PRIMARY KEY AUTO_INCREMENT,
    group_id   BIGINT NOT NULL,
    user_id    BIGINT NOT NULL,
    role       ENUM('owner','admin','member') DEFAULT 'member',
    joined_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES `groups`(id),
    FOREIGN KEY (user_id)  REFERENCES users(id),
    UNIQUE KEY uq_group_member (group_id, user_id)
);
```

### 5.5 消息表 `messages`

```sql
CREATE TABLE messages (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    sender_id    BIGINT NOT NULL,
    -- 私聊时 receiver_id 有值，group_id 为 NULL；群聊反之
    receiver_id  BIGINT,
    group_id     BIGINT,
    msg_type     ENUM('text','image','file','audio','system') DEFAULT 'text',
    content      TEXT NOT NULL,                    -- 文本内容 或 文件路径
    file_name    VARCHAR(256),                     -- 文件原始名称
    file_size    BIGINT,                           -- 字节数
    is_recalled  BOOLEAN DEFAULT FALSE,            -- 是否撤回
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id)   REFERENCES users(id),
    FOREIGN KEY (receiver_id) REFERENCES users(id),
    FOREIGN KEY (group_id)    REFERENCES `groups`(id),
    INDEX idx_private_chat (sender_id, receiver_id, created_at),
    INDEX idx_group_chat   (group_id, created_at)
);
```

### 5.6 消息已读状态表 `message_reads`

```sql
CREATE TABLE message_reads (
    id         BIGINT PRIMARY KEY AUTO_INCREMENT,
    message_id BIGINT NOT NULL,
    user_id    BIGINT NOT NULL,
    read_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id),
    FOREIGN KEY (user_id)    REFERENCES users(id),
    UNIQUE KEY uq_read (message_id, user_id)
);
```

### 5.7 朋友圈动态表 `moments`

```sql
CREATE TABLE moments (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT NOT NULL,
    content     TEXT,
    images      JSON,                              -- 图片路径数组
    visibility  ENUM('public','friends','private') DEFAULT 'friends',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 5.8 朋友圈评论/点赞表 `moment_interactions`

```sql
CREATE TABLE moment_interactions (
    id         BIGINT PRIMARY KEY AUTO_INCREMENT,
    moment_id  BIGINT NOT NULL,
    user_id    BIGINT NOT NULL,
    type       ENUM('like','comment') NOT NULL,
    content    VARCHAR(512),                       -- 评论内容，点赞为空
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (moment_id) REFERENCES moments(id),
    FOREIGN KEY (user_id)   REFERENCES users(id)
);
```

### Redis 数据结构规划

```
# 用户在线状态
online:{user_id}  →  STRING  "1"  (TTL: 心跳30s刷新)

# JWT Token 黑名单（登出后加入）
blacklist:token:{jti}  →  STRING  "1"  (TTL: token过期时间)

# 用户 WebSocket 连接 ID
ws_conn:{user_id}  →  STRING  connection_id

# 未读消息计数
unread:{user_id}:{conversation_id}  →  STRING  "5"

# 消息队列（离线用户的待推送消息）
msg_queue:{user_id}  →  LIST  [message_json, ...]
```

---

## 6. 分阶段任务拆解

### Phase 1 — MVP核心（私聊能跑起来）
**预计时间：3～4周**

**目标：** 用户能注册登录，加好友，发送/接收文字消息

- [ ] 后端项目初始化（FastAPI + SQLAlchemy + Alembic）
- [ ] 数据库连接配置（MySQL + Redis）
- [ ] 用户注册 / 登录 API（JWT 鉴权）
- [ ] 好友添加 / 同意 / 拒绝 API
- [ ] WebSocket 连接管理器（ConnectionManager）
- [ ] 私聊消息收发（WebSocket）
- [ ] 消息历史记录查询 API
- [ ] 前端项目初始化（Vue 3 + Vite + Element Plus）
- [ ] 登录 / 注册页面
- [ ] 主聊天页面布局（侧边栏 + 联系人列表 + 聊天窗口）
- [ ] WebSocket 客户端封装
- [ ] 消息气泡组件
- [ ] 联调测试

**Milestone：两个账号能在本地实时聊天 ✅**

---

### Phase 2 — 聊天功能完善
**预计时间：3～4周**

**目标：** 群聊、图片/文件发送、已读状态、消息撤回

- [ ] 群组创建 / 加入 / 退出 API
- [ ] 群聊 WebSocket 消息广播
- [ ] 文件/图片上传接口（本地存储）
- [ ] 消息类型扩展（image / file）
- [ ] 消息已读/未读状态
- [ ] 未读消息计数（Redis）
- [ ] 消息撤回功能
- [ ] 用户在线/离线状态显示（Redis TTL心跳）
- [ ] 前端：群聊界面
- [ ] 前端：图片预览 / 文件下载
- [ ] 前端：未读消息小红点

**Milestone：群聊可用，支持图片文件，有已读状态 ✅**

---

### Phase 3 — 社交功能
**预计时间：2～3周**

**目标：** 朋友圈、好友搜索、用户个人资料

- [ ] 朋友圈发布 / 查看 / 点赞 / 评论 API
- [ ] 用户搜索（按用户名）
- [ ] 用户个人资料页 / 修改资料
- [ ] 头像上传
- [ ] 好友申请通知（WebSocket 推送）
- [ ] 前端：朋友圈页面
- [ ] 前端：个人资料页

**Milestone：有朋友圈，有通知推送 ✅**

---

### Phase 4 — 体验优化
**预计时间：2周**

**目标：** 细节打磨，接近完整产品体验

- [ ] 消息搜索（本地聊天记录）
- [ ] @成员功能（群聊）
- [ ] 图片/消息多选转发
- [ ] 消息通知（浏览器 Notification API）
- [ ] 输入中状态显示（"对方正在输入..."）
- [ ] 表情包支持
- [ ] 深色模式

**Milestone：体验接近微信基础版 ✅**

---

### Phase 5 — 部署上线
**预计时间：1～2周**

**目标：** Docker 化，部署到云服务器，域名+HTTPS

- [ ] 编写 Dockerfile（前端 + 后端）
- [ ] docker-compose.yml 编排（nginx + backend + mysql + redis）
- [ ] Nginx 配置（反向代理 + 静态文件 + WebSocket）
- [ ] 购买云服务器 + 域名
- [ ] SSL 证书配置（Let's Encrypt）
- [ ] 环境变量 / 生产配置分离
- [ ] 数据库备份策略

**Milestone：朋友可以通过域名访问使用 ✅**

---

### Phase 6 — 移动端 & 进阶
**预计时间：持续迭代**

- [ ] 迁移文件存储至阿里云 OSS
- [ ] React Native 或 Flutter 移动端
- [ ] 语音/视频通话（WebRTC）
- [ ] 端对端消息加密
- [ ] 消息全文搜索（Elasticsearch）

---

## 7. API 接口规范

### 基础规范

```
Base URL: http://localhost:8000/api/v1
认证方式: Bearer Token (JWT)
请求格式: application/json
响应格式: application/json
```

### 响应结构

```json
{
  "code": 200,
  "message": "success",
  "data": { }
}
```

### 主要接口列表

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 认证 | POST | /auth/register | 注册 |
| 认证 | POST | /auth/login | 登录 |
| 认证 | POST | /auth/refresh | 刷新 Token |
| 用户 | GET | /users/me | 获取当前用户信息 |
| 用户 | PUT | /users/me | 修改个人资料 |
| 用户 | GET | /users/search?q= | 搜索用户 |
| 好友 | GET | /friends | 好友列表 |
| 好友 | POST | /friends/request | 发送好友申请 |
| 好友 | PUT | /friends/request/{id} | 处理好友申请 |
| 消息 | GET | /messages/private/{user_id} | 私聊历史 |
| 消息 | GET | /messages/group/{group_id} | 群聊历史 |
| 群组 | POST | /groups | 创建群组 |
| 群组 | GET | /groups/{id}/members | 群成员列表 |
| 文件 | POST | /files/upload | 上传文件 |
| 朋友圈 | GET | /moments | 朋友圈列表 |
| 朋友圈 | POST | /moments | 发布动态 |

---

## 8. WebSocket 消息协议

### 连接地址
```
ws://localhost:8000/ws?token={jwt_token}
```

### 消息格式（JSON）

```json
{
  "type": "消息类型",
  "data": { }
}
```

### 消息类型定义

| type | 方向 | 说明 |
|------|------|------|
| `private_message` | 双向 | 私聊消息 |
| `group_message` | 双向 | 群聊消息 |
| `message_read` | 客户端→服务端 | 已读回执 |
| `message_recall` | 双向 | 消息撤回 |
| `friend_request` | 服务端→客户端 | 好友申请通知 |
| `user_online` | 服务端→客户端 | 好友上线通知 |
| `user_offline` | 服务端→客户端 | 好友下线通知 |
| `typing` | 双向 | 正在输入状态 |
| `ping` | 客户端→服务端 | 心跳 |
| `pong` | 服务端→客户端 | 心跳响应 |

### 示例：发送私聊消息

```json
// 客户端发送
{
  "type": "private_message",
  "data": {
    "receiver_id": 42,
    "msg_type": "text",
    "content": "你好！"
  }
}

// 服务端广播给接收方
{
  "type": "private_message",
  "data": {
    "id": 1001,
    "sender_id": 7,
    "sender_nickname": "Yuan",
    "receiver_id": 42,
    "msg_type": "text",
    "content": "你好！",
    "created_at": "2025-01-01T12:00:00Z"
  }
}
```

---

## 9. 开发规范

### Git 分支规范
```
main          生产分支，只合并经过测试的代码
dev           开发主分支
feature/xxx   功能分支，开发完成后合并到 dev
fix/xxx       Bug 修复分支
```

### Commit 规范
```
feat: 添加用户注册功能
fix: 修复 WebSocket 断线重连问题
docs: 更新 API 文档
refactor: 重构消息服务层
test: 添加认证单元测试
```

### 环境变量（.env 文件，不提交 Git）
```env
# 数据库
DATABASE_URL=mysql+asyncmy://root:password@localhost:3306/powerchat
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-super-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# 文件上传
UPLOAD_DIR=./app/static/uploads
MAX_FILE_SIZE=20971520   # 20MB

# 服务配置
DEBUG=True
CORS_ORIGINS=["http://localhost:5173"]
```

---

## 下一步行动

准备好后，我们从 **Phase 1 第一个任务** 开始：

1. 创建 `PowerChat/` 目录结构
2. 初始化 FastAPI 后端项目
3. 配置 MySQL + Redis 连接
4. 写第一个接口：用户注册

**Let's build! 🚀**
