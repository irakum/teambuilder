from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_organizer_token
from app.schemas.schemas import (
    DistributeIn, MoveParticipantIn, SessionOut,
)
from app.services.distribution_service import DistributionService
from app.services.export import ExportService

router = APIRouter(prefix="/sessions/{session_id}", tags=["distribution"])


@router.post("/distribute", response_model=SessionOut)
async def distribute(
    session_id: UUID,
    body: DistributeIn,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_organizer_token),
):
    """
    Запускає алгоритм розподілу учасників у команди.
    Якщо розподіл вже виконувався — скидає попередні результати і запускає знову.
    """
    service = DistributionService(db)
    session = await service.run(
        session_id=session_id,
        token=token,
        use_compatibility=body.use_compatibility,
        balance_threshold=body.balance_threshold,
    )
    return SessionOut.from_orm_full(session)


@router.patch("/move-participant", response_model=SessionOut)
async def move_participant(
    session_id: UUID,
    body: MoveParticipantIn,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(get_organizer_token),
):
    """Переміщує учасника до іншої команди вручну."""
    service = DistributionService(db)
    session = await service.move_participant(
        session_id=session_id,
        token=token,
        participant_id=body.participant_id,
        target_team_id=body.target_team_id,
    )
    return SessionOut.from_orm_full(session)


@router.get("/export/csv")
async def export_csv(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Завантажує результати розподілу у форматі CSV."""
    service = ExportService(db)
    content = await service.to_csv(session_id)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename=session_{session_id}.csv"},
    )


@router.get("/export/pdf")
async def export_pdf(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Завантажує результати розподілу у форматі PDF."""
    service = ExportService(db)
    content = await service.to_pdf(session_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=session_{session_id}.pdf"},
    )
