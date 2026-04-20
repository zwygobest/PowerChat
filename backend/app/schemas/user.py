from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    nickname: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    nickname: str
    avatar_url: str | None = None
    bio: str = ""
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
