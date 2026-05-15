import json
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.models.participant import Participant
from app.models.participant_skill import ParticipantSkill
from app.models.skill import Skill
from app.repositories.base import BaseRepository


class ParticipantRepository(BaseRepository[Participant]):
    model = Participant

    def _tags_to_db(self, tags: list[str]) -> str:
        return json.dumps(tags, ensure_ascii=False)

    async def get_with_skills(self, id: UUID) -> Participant | None:
        result = await self.db.execute(
            select(Participant)
            .where(Participant.id == id)
            .options(
                selectinload(Participant.skills).selectinload(ParticipantSkill.skill)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: UUID) -> list[Participant]:
        result = await self.db.execute(
            select(Participant)
            .where(Participant.session_id == session_id)
            .options(
                selectinload(Participant.skills).selectinload(ParticipantSkill.skill)
            )
            .order_by(Participant.name)
        )
        return list(result.scalars().all())

    async def create(
        self,
        session_id: UUID,
        name: str,
        compatibility_tags: list[str],
    ) -> Participant:
        participant = Participant(
            session_id=session_id,
            name=name,
            compatibility_tags=self._tags_to_db(compatibility_tags),
        )
        self.db.add(participant)
        await self.db.flush()
        await self.db.refresh(participant)
        return participant

    async def update(
        self,
        participant: Participant,
        name: str | None,
        compatibility_tags: list[str] | None,
    ) -> Participant:
        if name is not None:
            participant.name = name
        if compatibility_tags is not None:
            participant.compatibility_tags = self._tags_to_db(compatibility_tags)
        await self.db.flush()
        return participant

    async def assign_team(self, participant: Participant, team_id: UUID) -> Participant:
        participant.team_id = team_id
        await self.db.flush()
        return participant

    async def update_score(self, participant: Participant, score: float) -> Participant:
        participant.total_score = score
        await self.db.flush()
        return participant

    async def unassign_all_teams(self, session_id: UUID) -> None:
        result = await self.db.execute(
            select(Participant).where(Participant.session_id == session_id)
        )
        for p in result.scalars().all():
            p.team_id = None
        await self.db.flush()

    async def delete_all_by_session(self, session_id: UUID) -> None:
        await self.db.execute(
            delete(Participant).where(Participant.session_id == session_id)
        )
        await self.db.flush()

    async def get_or_create_skill(self, name: str) -> Skill:
        result = await self.db.execute(select(Skill).where(Skill.name == name))
        skill = result.scalar_one_or_none()
        if skill is None:
            skill = Skill(name=name)
            self.db.add(skill)
            await self.db.flush()
            await self.db.refresh(skill)
        return skill

    async def set_skills(
        self,
        participant: Participant,
        skills: list[dict],
    ) -> Participant:
        await self.db.execute(
            delete(ParticipantSkill).where(
                ParticipantSkill.participant_id == participant.id
            )
        )
        for entry in skills:
            skill = await self.get_or_create_skill(entry["name"])
            ps = ParticipantSkill(
                participant_id=participant.id,
                skill_id=skill.id,
                level=entry["level"],
            )
            self.db.add(ps)

        await self.db.flush()
        await self.db.refresh(participant)
        return participant