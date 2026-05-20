import uuid
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, Enum, Uuid, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SessionStatus(str, PyEnum):
    pending = "pending"        # учасники додані, розподіл ще не запущено
    distributed = "distributed"  # розподіл виконано
    closed = "closed"          # сесія закрита, дані можна видалити


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    team_count: Mapped[int] = mapped_column(Integer, nullable=False)
    min_team_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_team_size: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    organizer_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), nullable=False, default=SessionStatus.pending
    )

    owner: Mapped["User | None"] = relationship(
        back_populates="sessions", foreign_keys=[owner_id]
    )
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    teams: Mapped[list["Team"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    invites: Mapped[list["Invite"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    organizers: Mapped[list["SessionOrganizer"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} name={self.name!r} status={self.status}>"
