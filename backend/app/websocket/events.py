"""WebSocket 事件类型常量。

入站（client → server）和出站（server → client）共用同一组事件名，
用 payload 里的字段区分语义。这样客户端只需要 switch 一个字段。
"""

# 入站
EVT_PRIVATE_MESSAGE = "private_message"  # 客户端发私聊：{type, receiver_id, content, msg_type?}
EVT_PING = "ping"                         # 心跳

# 出站
EVT_NEW_MESSAGE = "new_message"           # 推给接收方：{type, message: MessageOut}
EVT_MESSAGE_ACK = "message_ack"           # 回给发送方确认：{type, message: MessageOut, client_msg_id?}
EVT_ERROR = "error"                       # 业务/协议错误（不断连）：{type, code, detail}
EVT_SYSTEM = "system"                     # 系统通知：{type, detail}
EVT_PONG = "pong"

# 错误码（细分到具体场景，便于前端判断）
ERR_INVALID_PAYLOAD = "invalid_payload"
ERR_UNKNOWN_EVENT = "unknown_event"
ERR_NOT_FRIEND = "not_friend"
ERR_RECEIVER_NOT_FOUND = "receiver_not_found"
ERR_SELF_MESSAGE = "self_message"
ERR_INTERNAL = "internal_error"
