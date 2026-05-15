from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, BusinessRuleError
from app.models.session import SessionStatus
from app.repositories.participant import ParticipantRepository
from app.repositories.session import SessionRepository
from app.repositories.team import TeamRepository
from app.services.distribution import (
    ParticipantInput,
    SkillEntry,
    distribute,
)


class DistributionService:
    def __init__(self, db: AsyncSession) -> None:
        self.session_repo = SessionRepository(db)
        self.participant_repo = ParticipantRepository(db)
        self.team_repo = TeamRepository(db)

    async def run(
        self,
        session_id: UUID,
        token: str,
        use_compatibility: bool = True,
        balance_threshold: float = 0.15,
    ):
        """
        Запускає повний цикл розподілу:
        1. Перевірка прав та стану сесії.
        2. Скидання попередніх результатів (якщо розподіл вже був).
        3. Побудова вхідних даних для алгоритму.
        4. Виконання алгоритму.
        5. Збереження результатів у БД.
        6. Оновлення статусу сесії.
        """
        # 1. Перевірка
        session = await self.session_repo.get_with_relations(session_id)
        if session is None:
            raise NotFoundError(f"Сесію {session_id} не знайдено")
        if session.organizer_token != token:
            from app.core.exceptions import ForbiddenError
            raise ForbiddenError("Невірний токен організатора")
        if session.status == SessionStatus.closed:
            raise BusinessRuleError("Сесія закрита — розподіл неможливий")

        participants = await self.participant_repo.list_by_session(session_id)
        if not participants:
            raise BusinessRuleError("Неможливо запустити розподіл: немає жодного учасника")
        if len(participants) < session.team_count:
            raise BusinessRuleError(
                f"Учасників ({len(participants)}) менше ніж команд ({session.team_count})"
            )

        # 2. Скидаємо попередній розподіл
        if session.status == SessionStatus.distributed:
            await self.participant_repo.unassign_all_teams(session_id)
            await self.team_repo.delete_all_by_session(session_id)

        # 3. Будуємо вхідні дані для алгоритму
        inputs: list[ParticipantInput] = [
            ParticipantInput(
                id=p.id,
                name=p.name,
                skills=[
                    SkillEntry(
                        name=ps.skill.name,
                        level=ps.level,
                        weight=ps.skill.weight,
                    )
                    for ps in p.skills
                ],
                compatibility_tags=p.tags_list if hasattr(p, 'tags_list') else p.compatibility_tags,
            )
            for p in participants
        ]

        # 4. Запускаємо алгоритм
        results = distribute(
            participants=inputs,
            team_count=session.team_count,
            use_compatibility=use_compatibility,
            balance_threshold=balance_threshold,
        )

        # 5. Зберігаємо результати
        teams = await self.team_repo.create_many(session_id, session.team_count)

        for team_result, team in zip(results, teams):
            await self.team_repo.update_score(team, team_result.total_score)
            for participant_id in team_result.participant_ids:
                participant = next(p for p in participants if p.id == participant_id)
                await self.participant_repo.assign_team(participant, team.id)

        # 6. Оновлюємо статус сесії
        await self.session_repo.update_status(session, SessionStatus.distributed)

        # Скидаємо кеш сесії щоб отримати свіжі дані з БД
        await self.session_repo.db.commit()
        self.session_repo.db.expire_all()

        # Повертаємо сесію зі свіжими даними
        return await self.session_repo.get_with_relations(session_id)

    async def move_participant(
        self,
        session_id: UUID,
        token: str,
        participant_id: UUID,
        target_team_id: UUID,
    ):
        """Ручне переміщення учасника між командами після розподілу."""
        session = await self.session_repo.get(session_id)
        if session is None:
            raise NotFoundError(f"Сесію {session_id} не знайдено")
        if session.organizer_token != token:
            from app.core.exceptions import ForbiddenError
            raise ForbiddenError("Невірний токен організатора")
        if session.status != SessionStatus.distributed:
            raise BusinessRuleError("Ручне коригування доступне лише після виконання розподілу")

        participant = await self.participant_repo.get(participant_id)
        if participant is None or participant.session_id != session_id:
            raise NotFoundError(f"Учасника {participant_id} не знайдено")

        target_team = await self.team_repo.get(target_team_id)
        if target_team is None or target_team.session_id != session_id:
            raise NotFoundError(f"Команду {target_team_id} не знайдено")

        # Оновлюємо рейтинги команд
        if participant.team_id:
            old_team = await self.team_repo.get(participant.team_id)
            if old_team:
                await self.team_repo.update_score(
                    old_team, old_team.total_score - participant.total_score
                )

        await self.team_repo.update_score(
            target_team, target_team.total_score + participant.total_score
        )
        await self.participant_repo.assign_team(participant, target_team_id)

        return await self.session_repo.get_with_relations(session_id)
