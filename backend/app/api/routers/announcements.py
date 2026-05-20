import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_db, get_current_user
from app.models.announcement import Announcement
from app.models.participant import Participant
from app.models.session import Session
from app.models.session_organizer import SessionOrganizer
from app.models.team import Team
from app.models.user import User

router = APIRouter(tags=["announcements"])


class AnnouncementIn(BaseModel):
    content: str
    audience: str          # "all" | "team" | "participant"
    team_id: str | None = None
    participant_id: str | None = None


class AudienceLabel(BaseModel):
    type: str
    label: str


class AnnouncementOut(BaseModel):
    id: str
    content: str
    audience: str
    audience_label: str    # "Всі учасники" / "Команда 1" / "Іван Петренко"
    sender_name: str
    sender_avatar: str | None
    created_at: str
    is_mine: bool          # чи поточний юзер є адресатом


def _is_organizer_sync(session: Session, user_id: UUID, organizers: list) -> bool:
    if str(session.owner_id) == str(user_id):
        return True
    return any(str(o.user_id) == str(user_id) for o in organizers)


async def _check_organizer(session_id: UUID, user: User, db: AsyncSession) -> Session:
    session_result = await db.execute(select(Session).where(Session.id == session_id))
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сесію не знайдено")

    if str(session.owner_id) == str(user.id):
        return session

    co_result = await db.execute(
        select(SessionOrganizer).where(
            SessionOrganizer.session_id == session_id,
            SessionOrganizer.user_id == user.id,
        )
    )
    if not co_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Тільки організатори можуть надсилати оголошення")
    return session


@router.post("/sessions/{session_id}/announcements", response_model=AnnouncementOut)
async def create_announcement(
    session_id: UUID,
    body: AnnouncementIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Організатор надсилає оголошення."""
    session = await _check_organizer(session_id, current_user, db)

    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Текст оголошення не може бути порожнім")

    if body.audience not in ("all", "team", "participant"):
        raise HTTPException(status_code=400, detail="Невірна аудиторія")

    team_id = UUID(body.team_id) if body.team_id else None
    participant_id = UUID(body.participant_id) if body.participant_id else None

    # Визначаємо мітку аудиторії
    audience_label = "Всі учасники"
    if body.audience == "team" and team_id:
        team_result = await db.execute(select(Team).where(Team.id == team_id))
        team = team_result.scalar_one_or_none()
        audience_label = team.name if team else "Команда"
    elif body.audience == "participant" and participant_id:
        part_result = await db.execute(select(Participant).where(Participant.id == participant_id))
        part = part_result.scalar_one_or_none()
        audience_label = part.name if part else "Учасник"

    ann = Announcement(
        id=uuid.uuid4(),
        session_id=session_id,
        sender_id=current_user.id,
        content=body.content.strip(),
        audience=body.audience,
        team_id=team_id,
        participant_id=participant_id,
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)

    # Зберігаємо сповіщення в таблицю messages і надсилаємо через WebSocket
    from app.api.routers.chat import manager
    from app.models.message import Message
    from datetime import datetime, timezone

    notification_text = f"📢 Нове оголошення для: {audience_label}. Перейдіть у розділ «Оголошення»."
    sid = str(session_id)

    async def _save_and_broadcast(channel_key: str, msg_channel: str, msg_team_id=None, msg_participant_id=None):
        msg = Message(
            id=uuid.uuid4(),
            session_id=session_id,
            sender_id=current_user.id,
            channel=msg_channel,
            team_id=msg_team_id,
            participant_id=msg_participant_id,
            content=notification_text,
            created_at=datetime.now(timezone.utc),
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)

        payload = {
            "type": "message",
            "message": {
                "id": str(msg.id),
                "channel": msg_channel,
                "sender_id": str(current_user.id),
                "sender_name": current_user.name,
                "sender_avatar": current_user.avatar_url,
                "content": notification_text,
                "created_at": msg.created_at.isoformat(),
                "team_id": str(msg_team_id) if msg_team_id else None,
                "participant_id": str(msg_participant_id) if msg_participant_id else None,
            }
        }
        await manager.broadcast(sid, channel_key, payload)

    if body.audience == "all":
        await _save_and_broadcast("general", "general")
    elif body.audience == "team" and team_id:
        await _save_and_broadcast(f"team:{team_id}", "team", msg_team_id=team_id)
    elif body.audience == "participant" and participant_id:
        await _save_and_broadcast(f"support:{participant_id}", "support", msg_participant_id=participant_id)

    return AnnouncementOut(
        id=str(ann.id),
        content=ann.content,
        audience=ann.audience,
        audience_label=audience_label,
        sender_name=current_user.name,
        sender_avatar=current_user.avatar_url,
        created_at=ann.created_at.isoformat(),
        is_mine=True,
    )


@router.get("/sessions/{session_id}/announcements", response_model=list[AnnouncementOut])
async def list_announcements(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Повертає оголошення для поточного юзера."""
    session_result = await db.execute(select(Session).where(Session.id == session_id))
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сесію не знайдено")

    # Перевіряємо роль
    co_result = await db.execute(
        select(SessionOrganizer).where(
            SessionOrganizer.session_id == session_id,
            SessionOrganizer.user_id == current_user.id,
        )
    )
    is_org = str(session.owner_id) == str(current_user.id) or co_result.scalar_one_or_none()

    # Знаходимо participant поточного юзера
    part_result = await db.execute(
        select(Participant).where(
            Participant.session_id == session_id,
            Participant.user_id == current_user.id,
        )
    )
    my_participant = part_result.scalar_one_or_none()

    # Завантажуємо оголошення
    result = await db.execute(
        select(Announcement)
        .where(Announcement.session_id == session_id)
        .options(
            selectinload(Announcement.sender),
            selectinload(Announcement.team),
            selectinload(Announcement.participant),
        )
        .order_by(Announcement.created_at.desc())
    )
    all_anns = result.scalars().all()

    output = []
    for ann in all_anns:
        # Організатор бачить всі оголошення
        if is_org:
            is_mine = True
        else:
            # Учасник бачить тільки свої
            if ann.audience == "all":
                is_mine = True
            elif ann.audience == "team" and my_participant:
                is_mine = str(ann.team_id) == str(my_participant.team_id)
            elif ann.audience == "participant" and my_participant:
                is_mine = str(ann.participant_id) == str(my_participant.id)
            else:
                is_mine = False

        if not is_mine and not is_org:
            continue

        # Мітка аудиторії
        if ann.audience == "all":
            audience_label = "Всі учасники"
        elif ann.audience == "team":
            audience_label = ann.team.name if ann.team else "Команда"
        else:
            audience_label = ann.participant.name if ann.participant else "Учасник"

        output.append(AnnouncementOut(
            id=str(ann.id),
            content=ann.content,
            audience=ann.audience,
            audience_label=audience_label,
            sender_name=ann.sender.name if ann.sender else "?",
            sender_avatar=ann.sender.avatar_url if ann.sender else None,
            created_at=ann.created_at.isoformat(),
            is_mine=is_mine,
        ))

    return output
