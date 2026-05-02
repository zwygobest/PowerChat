from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.message import MessageOut
from app.services import message_service

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/private/{user_id}", response_model=list[MessageOut])
async def list_private_history(
    user_id: int,
    limit: int = Query(50, ge=1, le=100),
    before_id: int | None = Query(None, ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    """拉取与某个好友的私聊历史。

    - `user_id`：对方的用户 ID
    - `limit`：每页条数（默认 50，最多 100）
    - `before_id`：游标分页，返回 id < before_id 的记录（首次请求不传）

    返回按 id DESC 排序（新→旧）。前端拿到后倒序展示即可。
    """
    msgs = await message_service.list_private_history(
        db,
        me_id=current_user.id,
        other_id=user_id,
        limit=limit,
        before_id=before_id,
    )
    return msgs
