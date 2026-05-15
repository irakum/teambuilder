import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.session import Session, SessionStatus
from app.models.team import Team
from app.models.participant import Participant
from app.models.participant_skill import ParticipantSkill
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    model = Session

    async def get_with_relations(self, id: UUID) -> Session | None:
        """Завантажує сесію з командами, учасниками та навичками."""
        result = await self.db.execute(
            select(Session)
            .where(Session.id == id)
            .options(
                selectinload(Session.participants).selectinload(
                    Participant.skills
                ).selectinload(ParticipantSkill.skill),
                selectinload(Session.teams).selectinload(
                    Team.participants
                ).selectinload(Participant.skills).selectinload(
                    ParticipantSkill.skill
                ),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> Session | None:
        result = await self.db.execute(
            select(Session).where(Session.organizer_token == token)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        team_count: int,
        min_team_size: int,
        max_team_size: int,
    ) -> Session:
        session = Session(
            name=name,
            team_count=team_count,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
            organizer_token=secrets.token_urlsafe(32),
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def update_status(self, session: Session, status: SessionStatus) -> Session:
        session.status = status
        await self.db.flush()
        return session
