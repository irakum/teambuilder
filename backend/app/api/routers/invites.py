import secrets
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_db, get_current_user, get_organizer_token
from app.models.invite import Invite
from app.models.session import Session
from app.models.user import User
from app.schemas.schemas import SessionOut, ParticipantOut

router = APIRouter(tags=["invites"])


class InviteOut(BaseModel):
    id: uuid.UUID
    code: str
    session_id: uuid.UUID
    invite_url: str


class SessionPublicOut(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    team_count: int
    participant_count: int


# ── Організатор генерує invite ────────────────────────────────────────────────

@router.post("/sessions/{session_id}/invites", response_model=InviteOut)
async def create_invite(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_organizer_token),
):
    """Генерує нове запрошення для сесії. Потрібен токен організатора."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сесію не знайдено")
    if session.organizer_token != token:
        raise HTTPException(status_code=403, detail="Невірний токен організатора")

    code = secrets.token_urlsafe(16)
    invite = Invite(session_id=session_id, code=code)
    db.add(invite)
    await db.flush()
    await db.refresh(invite)

    return InviteOut(
        id=invite.id,
        code=invite.code,
        session_id=invite.session_id,
        invite_url=f"/join/{invite.code}",
    )


@router.get("/sessions/{session_id}/invites", response_model=list[InviteOut])
async def list_invites(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_organizer_token),
):
    """Повертає всі запрошення для сесії."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сесію не знайдено")
    if session.organizer_token != token:
        raise HTTPException(status_code=403, detail="Невірний токен організатора")

    invites_result = await db.execute(
        select(Invite).where(Invite.session_id == session_id)
    )
    invites = invites_result.scalars().all()
    return [
        InviteOut(
            id=inv.id,
            code=inv.code,
            session_id=inv.session_id,
            invite_url=f"/join/{inv.code}",
        )
        for inv in invites
    ]


# ── Публічний ендпоінт — інфо про сесію по коду запрошення ───────────────────

@router.get("/invite/{code}/me", response_model=ParticipantOut)
async def get_my_participant(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Повертає учасника поточного юзера в сесії (по email), або 404."""
    result = await db.execute(select(Invite).where(Invite.code == code))
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Запрошення не знайдено")

    from sqlalchemy.orm import selectinload
    from app.models.participant import Participant
    from app.models.participant_skill import ParticipantSkill

    result = await db.execute(
        select(Participant)
        .where(
            Participant.session_id == invite.session_id,
            Participant.email == current_user.email,
        )
        .options(
            selectinload(Participant.skills).selectinload(ParticipantSkill.skill)
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=404, detail="Ви не є учасником цього хакатону")

    # Прив'язуємо user_id якщо ще не прив'язаний
    if participant.user_id is None:
        participant.user_id = current_user.id
        await db.flush()

    return ParticipantOut.from_orm_with_skills(participant)


@router.get("/invite/{code}", response_model=SessionOut)
async def get_session_by_invite(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Повертає публічну інформацію про сесію по коду запрошення."""
    result = await db.execute(
        select(Invite).where(Invite.code == code)
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Запрошення не знайдено або застаріло")

    from app.repositories.session import SessionRepository
    from app.services.session import SessionService
    service = SessionService(db)
    session = await service.get(invite.session_id)
    return SessionOut.from_orm_full(session, include_token=False)
