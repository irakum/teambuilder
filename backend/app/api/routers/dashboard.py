from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_db, get_current_user
from app.models.session import Session
from app.models.participant import Participant
from app.models.session_organizer import SessionOrganizer
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class SessionSummary(BaseModel):
    id: str
    name: str
    status: str
    team_count: int
    participant_count: int
    role: str  # "owner", "co-organizer", "participant"
    organizer_token: str | None = None


@router.get("/sessions", response_model=list[SessionSummary])
async def get_my_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Повертає всі сесії де користувач власник, співорганізатор або учасник."""
    result = []
    seen_ids = set()

    # Сесії де власник
    owner_result = await db.execute(
        select(Session)
        .where(Session.owner_id == current_user.id)
        .options(selectinload(Session.participants))
        .order_by(Session.name)
    )
    for session in owner_result.scalars().all():
        seen_ids.add(session.id)
        result.append(SessionSummary(
            id=str(session.id),
            name=session.name,
            status=session.status.value,
            team_count=session.team_count,
            participant_count=len(session.participants),
            role="owner",
            organizer_token=session.organizer_token,
        ))

    # Сесії де співорганізатор
    co_result = await db.execute(
        select(SessionOrganizer)
        .where(SessionOrganizer.user_id == current_user.id)
    )
    for co in co_result.scalars().all():
        if co.session_id in seen_ids:
            continue
        seen_ids.add(co.session_id)
        session_result = await db.execute(
            select(Session)
            .where(Session.id == co.session_id)
            .options(selectinload(Session.participants))
        )
        session = session_result.scalar_one_or_none()
        if session:
            result.append(SessionSummary(
                id=str(session.id),
                name=session.name,
                status=session.status.value,
                team_count=session.team_count,
                participant_count=len(session.participants),
                role="co-organizer",
                organizer_token=session.organizer_token,
            ))

    # Сесії де учасник
    part_result = await db.execute(
        select(Participant)
        .where(Participant.user_id == current_user.id)
        .options(selectinload(Participant.session))
    )
    for participant in part_result.scalars().all():
        session = participant.session
        if not session or session.id in seen_ids:
            continue
        seen_ids.add(session.id)
        count_result = await db.execute(
            select(Participant).where(Participant.session_id == session.id)
        )
        count = len(count_result.scalars().all())
        result.append(SessionSummary(
            id=str(session.id),
            name=session.name,
            status=session.status.value,
            team_count=session.team_count,
            participant_count=count,
            role="participant",
        ))

    return result
