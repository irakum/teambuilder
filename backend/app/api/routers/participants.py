from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_organizer_token, get_optional_user
from app.models.user import User
from app.schemas.schemas import (
    ParticipantIn, ParticipantUpdate, ParticipantOut,
    ImportResultOut, MessageOut,
)
from app.services.participant import ParticipantService

router = APIRouter(
    prefix="/sessions/{session_id}/participants",
    tags=["participants"],
)


@router.get("/me", response_model=ParticipantOut)
async def get_my_participant(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Повертає учасника поточного юзера в сесії (по email), або 404."""
    if not current_user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Необхідна авторизація")

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.participant import Participant
    from app.models.participant_skill import ParticipantSkill

    result = await db.execute(
        select(Participant)
        .where(
            Participant.session_id == session_id,
            Participant.email == current_user.email,
        )
        .options(
            selectinload(Participant.skills).selectinload(ParticipantSkill.skill)
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Ви не є учасником цієї сесії")

    if participant.user_id is None:
        participant.user_id = current_user.id
        await db.flush()

    return ParticipantOut.from_orm_with_skills(participant)


@router.get("", response_model=list[ParticipantOut])
async def list_participants(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Повертає список усіх учасників сесії з навичками."""
    service = ParticipantService(db)
    participants = await service.repo.list_by_session(session_id)
    return [ParticipantOut.from_orm_with_skills(p) for p in participants]


@router.post("", response_model=ParticipantOut, status_code=status.HTTP_201_CREATED)
async def add_participant(
    session_id: UUID,
    body: ParticipantIn,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_organizer_token),
):
    """Додає одного учасника до сесії."""
    service = ParticipantService(db)
    participant = await service.add(
        session_id=session_id,
        name=body.name,
        email=body.email,
        skills=[s.model_dump() for s in body.skills],
        compatibility_tags=body.compatibility_tags,
    )
    return ParticipantOut.from_orm_with_skills(participant)


@router.post("/import", response_model=ImportResultOut, status_code=status.HTTP_201_CREATED)
async def import_participants(
    session_id: UUID,
    file: UploadFile = File(..., description="CSV-файл з учасниками"),
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_organizer_token),
):
    """
    Імпортує учасників з CSV-файлу.

    Очікуваний формат:
    ```
    name,skills,tags
    Іван Петренко,"Python:4,Design:3","leader,backend"
    ```
    """
    content = await file.read()
    service = ParticipantService(db)
    created = await service.import_csv(session_id, content)
    return ImportResultOut(
        imported=len(created),
        message=f"Успішно імпортовано {len(created)} учасників",
    )


@router.patch("/{participant_id}", response_model=ParticipantOut)
async def update_participant(
    session_id: UUID,
    participant_id: UUID,
    body: ParticipantUpdate,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_organizer_token),
):
    """Оновлює дані учасника. Передавай лише поля, які змінились."""
    service = ParticipantService(db)
    participant = await service.update(
        session_id=session_id,
        participant_id=participant_id,
        name=body.name,
        skills=[s.model_dump() for s in body.skills] if body.skills is not None else None,
        compatibility_tags=body.compatibility_tags,
    )
    return ParticipantOut.from_orm_with_skills(participant)


@router.delete("/{participant_id}", response_model=MessageOut)
async def delete_participant(
    session_id: UUID,
    participant_id: UUID,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_organizer_token),
):
    """Видаляє учасника з сесії."""
    service = ParticipantService(db)
    await service.delete(session_id, participant_id)
    return MessageOut(message="Учасника видалено")
