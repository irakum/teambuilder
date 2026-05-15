import uuid

from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.types import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Теги сумісності — зберігаємо як JSON (працює і в SQLite і в PostgreSQL)
    compatibility_tags: Mapped[str] = mapped_column(
        String(1000), nullable=False, default="[]"
    )

    @property
    def tags_list(self) -> list[str]:
        import json as _j
        if not self.compatibility_tags:
            return []
        if isinstance(self.compatibility_tags, list):
            return self.compatibility_tags
        try:
            return _j.loads(self.compatibility_tags)
        except Exception:
            return []

    session: Mapped["Session"] = relationship(back_populates="participants")
    team: Mapped["Team | None"] = relationship(back_populates="participants")
    skills: Mapped[list["ParticipantSkill"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Participant id={self.id} name={self.name!r}>"
