import csv
import io
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, BusinessRuleError
from app.models.participant import Participant
from app.models.session import SessionStatus
from app.repositories.participant import ParticipantRepository
from app.repositories.session import SessionRepository


# Очікувані заголовки CSV (регістронезалежно)
CSV_FIELD_NAME = "name"
CSV_FIELD_SKILLS = "skills"   # формат: "Python:4,Design:3"
CSV_FIELD_TAGS = "tags"       # формат: "leader,backend"


class ParticipantService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ParticipantRepository(db)
        self.session_repo = SessionRepository(db)

    async def _get_active_session(self, session_id: UUID):
        """Перевіряє що сесія існує і ще не закрита."""
        session = await self.session_repo.get(session_id)
        if session is None:
            raise NotFoundError(f"Сесію {session_id} не знайдено")
        if session.status == SessionStatus.closed:
            raise BusinessRuleError("Сесія закрита — додавання учасників неможливе")
        return session

    async def add(
        self,
        session_id: UUID,
        name: str,
        skills: list[dict],
        compatibility_tags: list[str],
    ) -> Participant:
        await self._get_active_session(session_id)
        self._validate_skills(skills)

        participant = await self.repo.create(
            session_id=session_id,
            name=name.strip(),
            compatibility_tags=compatibility_tags,
        )
        if skills:
            await self.repo.set_skills(participant, skills)

        # Перезавантажуємо з БД щоб мати skills з selectinload
        participant = await self.repo.get_with_skills(participant.id)

        # Одразу рахуємо рейтинг щоб не робити це пізніше
        from app.services.distribution import calc_score, ParticipantInput, SkillEntry
        p_input = ParticipantInput(
            id=participant.id,
            name=participant.name,
            skills=[
                SkillEntry(
                    name=ps.skill.name,
                    level=ps.level,
                    weight=ps.skill.weight,
                )
                for ps in participant.skills
            ],
        )
        await self.repo.update_score(participant, calc_score(p_input))
        return participant

    async def update(
        self,
        session_id: UUID,
        participant_id: UUID,
        name: str | None,
        skills: list[dict] | None,
        compatibility_tags: list[str] | None,
    ) -> Participant:
        await self._get_active_session(session_id)
        participant = await self.repo.get_with_skills(participant_id)
        if participant is None or participant.session_id != session_id:
            raise NotFoundError(f"Учасника {participant_id} не знайдено")

        if skills is not None:
            self._validate_skills(skills)

        participant = await self.repo.update(participant, name, compatibility_tags)

        if skills is not None:
            await self.repo.set_skills(participant, skills)

        # Перезавантажуємо з БД щоб мати skills з selectinload
        participant = await self.repo.get_with_skills(participant.id)

        # Перераховуємо рейтинг
        from app.services.distribution import calc_score, ParticipantInput, SkillEntry
        p_input = ParticipantInput(
            id=participant.id,
            name=participant.name,
            skills=[
                SkillEntry(ps.skill.name, ps.level, ps.skill.weight)
                for ps in participant.skills
            ],
        )
        await self.repo.update_score(participant, calc_score(p_input))
        return participant

    async def delete(self, session_id: UUID, participant_id: UUID) -> None:
        await self._get_active_session(session_id)
        participant = await self.repo.get(participant_id)
        if participant is None or participant.session_id != session_id:
            raise NotFoundError(f"Учасника {participant_id} не знайдено")
        await self.repo.delete(participant)

    async def import_csv(
        self,
        session_id: UUID,
        content: bytes,
    ) -> list[Participant]:
        """
        Імпортує учасників з CSV-файлу.

        Очікуваний формат (перший рядок — заголовки):
            name,skills,tags
            Іван Петренко,"Python:4,Design:3","leader,backend"
            Оля Коваль,"React:5",""

        Поля skills і tags — необов'язкові.
        """
        await self._get_active_session(session_id)

        text = content.decode("utf-8-sig")  # utf-8-sig знімає BOM якщо є (Excel)
        reader = csv.DictReader(io.StringIO(text))

        # Нормалізуємо заголовки до нижнього регістру
        if reader.fieldnames is None:
            raise BusinessRuleError("CSV-файл порожній або не містить заголовків")
        reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]

        if CSV_FIELD_NAME not in reader.fieldnames:
            raise BusinessRuleError(
                f"CSV-файл має містити колонку '{CSV_FIELD_NAME}'"
            )

        created: list[Participant] = []
        for i, row in enumerate(reader, start=2):  # рядок 2 = перший після заголовка
            name = (row.get(CSV_FIELD_NAME) or "").strip()
            if not name:
                continue  # пропускаємо порожні рядки

            raw_skills = row.get(CSV_FIELD_SKILLS, "") or ""
            raw_tags = row.get(CSV_FIELD_TAGS, "") or ""

            skills = self._parse_skills_string(raw_skills, row_num=i)
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

            participant = await self.add(session_id, name, skills, tags)
            created.append(participant)

        return created

    # ── Приватні допоміжні методи ─────────────────────────────────────────────

    @staticmethod
    def _validate_skills(skills: list[dict]) -> None:
        for s in skills:
            if not isinstance(s.get("name"), str) or not s["name"].strip():
                raise BusinessRuleError("Назва навички не може бути порожньою")
            level = s.get("level")
            if not isinstance(level, int) or not (1 <= level <= 5):
                raise BusinessRuleError(
                    f"Рівень навички '{s.get('name')}' має бути цілим числом від 1 до 5"
                )

    @staticmethod
    def _parse_skills_string(raw: str, row_num: int) -> list[dict]:
        """Розбирає рядок 'Python:4,Design:3' у список dict."""
        skills = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" not in part:
                raise BusinessRuleError(
                    f"Рядок {row_num}: невірний формат навички '{part}'. "
                    f"Очікується 'Назва:Рівень', наприклад 'Python:4'"
                )
            name, _, level_str = part.partition(":")
            try:
                level = int(level_str.strip())
            except ValueError:
                raise BusinessRuleError(
                    f"Рядок {row_num}: рівень навички '{name.strip()}' має бути числом"
                )
            skills.append({"name": name.strip(), "level": level})
        return skills