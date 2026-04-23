from fastapi import HTTPException, status
from sqlalchemy import case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.friendship import Friendship, FriendshipStatus
from app.models.user import User
from app.schemas.friendship import FriendOut


async def send_request(db: AsyncSession, me: User, receiver_id: int) -> Friendship:
    if receiver_id == me.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot send friend request to yourself",
        )

    receiver = await db.get(User, receiver_id)
    if receiver is None or not receiver.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="receiver not found",
        )

    # 一次查出 me <-> receiver_id 之间任何方向的所有现有关系（最多 2 条）
    result = await db.scalars(
        select(Friendship).where(
            or_(
                (Friendship.requester_id == me.id)
                & (Friendship.receiver_id == receiver_id),
                (Friendship.requester_id == receiver_id)
                & (Friendship.receiver_id == me.id),
            )
        )
    )
    records = list(result)
    same_dir = next((r for r in records if r.requester_id == me.id), None)
    reverse_dir = next((r for r in records if r.requester_id == receiver_id), None)

    if any(r.status == FriendshipStatus.accepted for r in records):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="already friends",
        )

    if same_dir is not None and same_dir.status == FriendshipStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="friend request already sent, waiting for response",
        )

    if reverse_dir is not None and reverse_dir.status == FriendshipStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="this user has already sent you a request; please respond to it",
        )

    # 同方向曾被拒：复用记录改回 pending（避免触发唯一约束）
    if same_dir is not None and same_dir.status == FriendshipStatus.rejected:
        same_dir.status = FriendshipStatus.pending
        await db.commit()
        await db.refresh(same_dir)
        return same_dir

    fr = Friendship(
        requester_id=me.id,
        receiver_id=receiver_id,
        status=FriendshipStatus.pending,
    )
    db.add(fr)
    await db.commit()
    await db.refresh(fr)
    return fr


async def respond_to_request(
    db: AsyncSession, me: User, friendship_id: int, action: str
) -> Friendship:
    fr = await db.get(Friendship, friendship_id)
    if fr is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="friend request not found",
        )
    if fr.receiver_id != me.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only the receiver can respond to this request",
        )
    if fr.status != FriendshipStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"request already {fr.status.value}",
        )

    fr.status = (
        FriendshipStatus.accepted if action == "accept" else FriendshipStatus.rejected
    )
    await db.commit()
    await db.refresh(fr)
    return fr


async def list_friends(db: AsyncSession, me: User) -> list[FriendOut]:
    # 对方的 user_id：我是 requester 时取 receiver，反之亦然
    other_id = case(
        (Friendship.requester_id == me.id, Friendship.receiver_id),
        else_=Friendship.requester_id,
    )

    stmt = (
        select(Friendship, User)
        .join(User, User.id == other_id)
        .where(
            Friendship.status == FriendshipStatus.accepted,
            or_(
                Friendship.requester_id == me.id,
                Friendship.receiver_id == me.id,
            ),
        )
        .order_by(Friendship.updated_at.desc())
    )

    rows = (await db.execute(stmt)).all()
    return [
        FriendOut(
            friendship_id=fr.id,
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            friended_at=fr.updated_at,
        )
        for fr, user in rows
    ]
