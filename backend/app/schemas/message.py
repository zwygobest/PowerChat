from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.message import MessageType


class PrivateMessageIn(BaseModel):
    receiver_id: int = Field(gt=0)
    content: str = Field(min_length=1, max_length=4000)
    msg_type: MessageType = MessageType.text


class MessageOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    msg_type: MessageType
    content: str
    is_recalled: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
