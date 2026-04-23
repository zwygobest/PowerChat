from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FriendRequestCreate(BaseModel):
    receiver_id: int = Field(gt=0)


class FriendRequestRespond(BaseModel):
    action: Literal["accept", "reject"]


class FriendOut(BaseModel):
    friendship_id: int
    id: int
    username: str
    nickname: str
    avatar_url: str | None = None
    friended_at: datetime

    model_config = ConfigDict(from_attributes=True)
