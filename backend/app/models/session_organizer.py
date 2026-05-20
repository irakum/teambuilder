import uuid

from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SessionOrganizer(Base):
    __tablename__ = "session_organizers"
    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_session_organizers_session_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # "owner" або "co-organizer"
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="co-organizer")

    session: Mapped["Session"] = relationship(back_populates="organizers")
    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<SessionOrganizer session={self.session_id} user={self.user_id} role={self.role}>"
