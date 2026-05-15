from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_organizer_token
from app.schemas.schemas import SessionIn, SessionOut, MessageOut
from app.services.session import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionIn, db: AsyncSession = Depends(get_db)):
    """
    Створює нову сесію розподілу.
    Повертає сесію **разом з токеном організатора** — збережи його,
    він більше не відображатиметься.
    """
    service = SessionService(db)
    session = await service.create(
        name=body.name,
        team_count=body.team_count,
        min_team_size=body.min_team_size,
        max_team_size=body.max_team_size,
    )
    # get_with_relations щоб повернути повний об'єкт
    session = await service.get(session.id)
    return SessionOut.from_orm_full(session, include_token=True)


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Повертає стан сесії з учасниками та командами. Токен не включається."""
    service = SessionService(db)
    session = await service.get(session_id)
    return SessionOut.from_orm_full(session, include_token=False)


@router.delete("/{session_id}", response_model=MessageOut)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_organizer_token),
):
    """Видаляє сесію разом з усіма учасниками і командами (CASCADE)."""
    service = SessionService(db)
    await service.delete(session_id, token)
    return MessageOut(message="Сесію видалено")


@router.patch("/{session_id}/close", response_model=SessionOut)
async def close_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_organizer_token),
):
    """Закриває сесію — після цього додавання учасників і розподіл неможливі."""
    service = SessionService(db)
    session = await service.close(session_id, token)
    session = await service.get(session.id)
    return SessionOut.from_orm_full(session)
