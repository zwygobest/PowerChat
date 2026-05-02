from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.friendship import Friendship, FriendshipStatus
from app.models.message import Message, MessageType
from app.models.user import User

MAX_HISTORY_LIMIT = 100


async def is_friend(db: AsyncSession, a_id: int, b_id: int) -> bool:
    if a_id == b_id:
        return False
    stmt = select(Friendship.id).where(
        Friendship.status == FriendshipStatus.accepted,
        or_(
            and_(Friendship.requester_id == a_id, Friendship.receiver_id == b_id),
            and_(Friendship.requester_id == b_id, Friendship.receiver_id == a_id),
        ),
    )
    return (await db.scalar(stmt)) is not None


async def save_private_message(
    db: AsyncSession,
    sender_id: int,
    receiver_id: int,
    content: str,
    msg_type: MessageType = MessageType.text,
) -> Message:
    if sender_id == receiver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot send message to yourself",
        )

    receiver = await db.get(User, receiver_id)
    if receiver is None or not receiver.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="receiver not found",
        )

    if not await is_friend(db, sender_id, receiver_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="you are not friends with this user",
        )

    msg = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        msg_type=msg_type,
        content=content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def list_private_history(
    db: AsyncSession,
    me_id: int,
    other_id: int,
    limit: int = 50,
    before_id: int | None = None,
) -> list[Message]:
    if not await is_friend(db, me_id, other_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="you are not friends with this user",
        )

    limit = max(1, min(limit, MAX_HISTORY_LIMIT))

    stmt = select(Message).where(
        or_(
            and_(Message.sender_id == me_id, Message.receiver_id == other_id),
            and_(Message.sender_id == other_id, Message.receiver_id == me_id),
        )
    )
    if before_id is not None:
        stmt = stmt.where(Message.id < before_id)
    stmt = stmt.order_by(Message.id.desc()).limit(limit)

    result = await db.scalars(stmt)
    return list(result)