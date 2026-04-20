from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=True)

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(creds.credentials)
    except JWTError:
        raise CREDENTIALS_EXCEPTION

    sub = payload.get("sub")
    if sub is None:
        raise CREDENTIALS_EXCEPTION

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise CREDENTIALS_EXCEPTION

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise CREDENTIALS_EXCEPTION

    return user
