from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.database import get_db
from app.schemas.auth import AuthResponse, LoginRequest
from app.schemas.user import UserCreate, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    user = await auth_service.register_user(db, payload)
    token = create_access_token(subject=user.id)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    user = await auth_service.authenticate_user(db, payload.username, payload.password)
    token = create_access_token(subject=user.id)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))
