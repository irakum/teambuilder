from fastapi import Header, HTTPException, status, Depends
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import UserRepository


async def get_organizer_token(
    x_organizer_token: str | None = Header(default=None, alias="X-Organizer-Token"),
) -> str:
    if not x_organizer_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Заголовок X-Organizer-Token є обов'язковим",
        )
    return x_organizer_token


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Перевіряє Bearer JWT токен і повертає поточного користувача."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Необхідна авторизація",
        )
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
        user_id: str = payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірний або прострочений токен",
        )
    repo = UserRepository(db)
    from uuid import UUID
    user = await repo.get(UUID(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Користувача не знайдено")
    return user


async def get_optional_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Як get_current_user але повертає None якщо токена немає."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(authorization, db)
    except HTTPException:
        return None
