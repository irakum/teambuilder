import uuid
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, Enum
from sqlalchemy.types import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SessionStatus(str, PyEnum):
    pending = "pending"
    distributed = "distributed"
    closed = "closed"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    team_count: Mapped[int] = mapped_column(Integer, nullable=False)
    min_team_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_team_size: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    organizer_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), nullable=False, default=SessionStatus.pending
    )

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    teams: Mapped[list["Team"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} name={self.name!r} status={self.status}>"
