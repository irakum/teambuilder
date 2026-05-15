import uuid

from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.types import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    session: Mapped["Session"] = relationship(back_populates="teams")
    participants: Mapped[list["Participant"]] = relationship(back_populates="team")

    def __repr__(self) -> str:
        return f"<Team id={self.id} name={self.name!r} score={self.total_score}>"
