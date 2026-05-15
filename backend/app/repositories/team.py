from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.models.team import Team
from app.models.participant import Participant
from app.models.participant_skill import ParticipantSkill
from app.repositories.base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    model = Team

    async def list_by_session(self, session_id: UUID) -> list[Team]:
        result = await self.db.execute(
            select(Team)
            .where(Team.session_id == session_id)
            .options(
                selectinload(Team.participants).selectinload(
                    Participant.skills
                ).selectinload(ParticipantSkill.skill)
            )
            .order_by(Team.name)
        )
        return list(result.scalars().all())

    async def create_many(self, session_id: UUID, count: int) -> list[Team]:
        teams = [
            Team(session_id=session_id, name=f"Команда {i + 1}")
            for i in range(count)
        ]
        self.db.add_all(teams)
        await self.db.flush()
        for t in teams:
            await self.db.refresh(t)
        return teams

    async def update_score(self, team: Team, score: float) -> Team:
        team.total_score = score
        await self.db.flush()
        return team

    async def delete_all_by_session(self, session_id: UUID) -> None:
        await self.db.execute(
            delete(Team).where(Team.session_id == session_id)
        )
        await self.db.flush()
