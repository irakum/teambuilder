import uuid

from sqlalchemy import String, Float
from sqlalchemy.types import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    participant_skills: Mapped[list["ParticipantSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Skill name={self.name!r} weight={self.weight}>"
