import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.models.session import Session
from app.models.session_organizer import SessionOrganizer
from app.models.user import User

router = APIRouter(tags=["organizers"])


class OrganizerOut(BaseModel):
    user_id: str
    email: str
    name: str
    avatar_url: str | None
    role: str


class InviteOrganizerIn(BaseModel):
    email: str


def _check_owner(session: Session, current_user: User) -> None:
    if str(session.owner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Тільки власник може керувати організаторами")


@router.get("/sessions/{session_id}/organizers", response_model=list[OrganizerOut])
async def list_organizers(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Повертає список організаторів сесії."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сесію не знайдено")

    # Власник
    owner_result = await db.execute(select(User).where(User.id == session.owner_id))
    owner = owner_result.scalar_one_or_none()
    organizers = []
    if owner:
        organizers.append(OrganizerOut(
            user_id=str(owner.id),
            email=owner.email,
            name=owner.name,
            avatar_url=owner.avatar_url,
            role="owner",
        ))

    # Співорганізатори
    co_result = await db.execute(
        select(SessionOrganizer).where(SessionOrganizer.session_id == session_id)
    )
    for co in co_result.scalars().all():
        user_result = await db.execute(select(User).where(User.id == co.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            organizers.append(OrganizerOut(
                user_id=str(user.id),
                email=user.email,
                name=user.name,
                avatar_url=user.avatar_url,
                role=co.role,
            ))

    return organizers


@router.post("/sessions/{session_id}/organizers", response_model=OrganizerOut)
async def add_organizer(
    session_id: UUID,
    body: InviteOrganizerIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Додає співорганізатора за email. Тільки для власника."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сесію не знайдено")
    _check_owner(session, current_user)

    # Знаходимо юзера за email
    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Користувача з таким email не знайдено")
    if str(user.id) == str(session.owner_id):
        raise HTTPException(status_code=400, detail="Цей користувач вже є власником")

    # Перевіряємо чи вже є
    existing = await db.execute(
        select(SessionOrganizer).where(
            SessionOrganizer.session_id == session_id,
            SessionOrganizer.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Цей користувач вже є організатором")

    co = SessionOrganizer(
        id=uuid.uuid4(),
        session_id=session_id,
        user_id=user.id,
        role="co-organizer",
    )
    db.add(co)
    await db.flush()

    return OrganizerOut(
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        role="co-organizer",
    )


@router.delete("/sessions/{session_id}/organizers/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organizer(
    session_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Видаляє співорганізатора. Тільки для власника."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сесію не знайдено")
    _check_owner(session, current_user)

    co_result = await db.execute(
        select(SessionOrganizer).where(
            SessionOrganizer.session_id == session_id,
            SessionOrganizer.user_id == user_id,
        )
    )
    co = co_result.scalar_one_or_none()
    if not co:
        raise HTTPException(status_code=404, detail="Організатора не знайдено")

    await db.delete(co)
    await db.flush()
