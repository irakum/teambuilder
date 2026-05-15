from typing import Generic, TypeVar, Type
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Базовий репозиторій з типовими CRUD-операціями."""

    model: Type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, id: UUID) -> ModelT | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[ModelT]:
        result = await self.db.execute(select(self.model))
        return list(result.scalars().all())

    async def delete(self, instance: ModelT) -> None:
        await self.db.delete(instance)
        await self.db.flush()
