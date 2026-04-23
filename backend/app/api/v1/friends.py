from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.friendship import FriendOut, FriendRequestCreate, FriendRequestRespond
from app.services import friend_service

router = APIRouter(prefix="/friends", tags=["friends"])


@router.get("", response_model=list[FriendOut])
async def list_my_friends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FriendOut]:
    return await friend_service.list_friends(db, current_user)


@router.post("/request", status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    payload: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    fr = await friend_service.send_request(db, current_user, payload.receiver_id)
    return {
        "friendship_id": fr.id,
        "requester_id": fr.requester_id,
        "receiver_id": fr.receiver_id,
        "status": fr.status.value,
    }


@router.put("/request/{friendship_id}")
async def respond_friend_request(
    friendship_id: int,
    payload: FriendRequestRespond,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    fr = await friend_service.respond_to_request(
        db, current_user, friendship_id, payload.action
    )
    return {
        "friendship_id": fr.id,
        "requester_id": fr.requester_id,
        "receiver_id": fr.receiver_id,
        "status": fr.status.value,
    }
