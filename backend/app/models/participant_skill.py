import uuid

from sqlalchemy import Integer, ForeignKey, UniqueConstraint
from sqlalchemy.types import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ParticipantSkill(Base):
    __tablename__ = "participant_skills"
    __table_args__ = (
        UniqueConstraint("participant_id", "skill_id", name="uq_participant_skill"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)

    participant: Mapped["Participant"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(back_populates="participant_skills")

    def __repr__(self) -> str:
        return f"<ParticipantSkill participant={self.participant_id} level={self.level}>"
