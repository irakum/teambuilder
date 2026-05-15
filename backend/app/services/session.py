from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ForbiddenError
from app.models.session import Session, SessionStatus
from app.repositories.session import SessionRepository


class SessionService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = SessionRepository(db)

    async def create(
        self,
        name: str,
        team_count: int,
        min_team_size: int = 1,
        max_team_size: int = 50,
    ) -> Session:
        if team_count < 2 or team_count > 20:
            from app.core.exceptions import BusinessRuleError
            raise BusinessRuleError("Кількість команд має бути від 2 до 20")
        if min_team_size > max_team_size:
            from app.core.exceptions import BusinessRuleError
            raise BusinessRuleError("Мінімальний розмір команди не може перевищувати максимальний")

        return await self.repo.create(
            name=name,
            team_count=team_count,
            min_team_size=min_team_size,
            max_team_size=max_team_size,
        )

    async def get(self, session_id: UUID) -> Session:
        session = await self.repo.get_with_relations(session_id)
        if session is None:
            raise NotFoundError(f"Сесію {session_id} не знайдено")
        return session

    async def verify_token(self, session_id: UUID, token: str) -> Session:
        """Повертає сесію якщо токен вірний, інакше кидає ForbiddenError."""
        session = await self.get(session_id)
        if session.organizer_token != token:
            raise ForbiddenError("Невірний токен організатора")
        return session

    async def close(self, session_id: UUID, token: str) -> Session:
        session = await self.verify_token(session_id, token)
        return await self.repo.update_status(session, SessionStatus.closed)

    async def delete(self, session_id: UUID, token: str) -> None:
        session = await self.verify_token(session_id, token)
        await self.repo.delete(session)
