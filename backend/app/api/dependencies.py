from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db  # noqa: F401 — re-exported for routers


async def get_organizer_token(
    x_organizer_token: str | None = Header(default=None, alias="X-Organizer-Token"),
) -> str:
    """
    Витягує токен організатора з заголовка X-Organizer-Token.
    Повертає 401 якщо заголовок відсутній.
    """
    if not x_organizer_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Заголовок X-Organizer-Token є обов'язковим",
        )
    return x_organizer_token
