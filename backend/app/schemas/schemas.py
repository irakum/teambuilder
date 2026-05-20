"""
Pydantic-схеми для всіх запитів і відповідей API.

Розділені на три блоки: Session, Participant, Distribution/Export.
"""

import uuid
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


# ── Спільні типи ──────────────────────────────────────────────────────────────

UUIDField = Annotated[uuid.UUID, Field()]


# ══════════════════════════════════════════════════════════════════════════════
# Skill
# ══════════════════════════════════════════════════════════════════════════════

class SkillIn(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Python"])
    level: int = Field(ge=1, le=5, examples=[4])

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class SkillOut(BaseModel):
    name: str
    level: int
    weight: float

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════════════
# Participant
# ══════════════════════════════════════════════════════════════════════════════

class ParticipantIn(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=["Іван Петренко"])
    email: str | None = Field(default=None, max_length=255, examples=["ivan@example.com"])
    skills: list[SkillIn] = Field(default_factory=list)
    compatibility_tags: list[str] = Field(default_factory=list, examples=[["leader"]])

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("compatibility_tags")
    @classmethod
    def clean_tags(cls, tags: list[str]) -> list[str]:
        return [t.strip().lower() for t in tags if t.strip()]


class ParticipantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    skills: list[SkillIn] | None = None
    compatibility_tags: list[str] | None = None


class ParticipantOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None = None
    total_score: float
    compatibility_tags: list[str]
    skills: list[SkillOut] = Field(default_factory=list)
    team_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_skills(cls, participant) -> "ParticipantOut":
        import json as _json
        raw = participant.compatibility_tags
        try:
            tags = _json.loads(raw) if raw else []
            if not isinstance(tags, list):
                tags = []
        except Exception:
            tags = []
        return cls(
            id=participant.id,
            name=participant.name,
            email=participant.email,
            total_score=participant.total_score,
            compatibility_tags=tags,
            team_id=participant.team_id,
            skills=[
                SkillOut(
                    name=ps.skill.name,
                    level=ps.level,
                    weight=ps.skill.weight,
                )
                for ps in participant.skills
            ],
        )


# ══════════════════════════════════════════════════════════════════════════════
# Team
# ══════════════════════════════════════════════════════════════════════════════

class TeamOut(BaseModel):
    id: uuid.UUID
    name: str
    total_score: float
    participants: list[ParticipantOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_full(cls, team) -> "TeamOut":
        return cls(
            id=team.id,
            name=team.name,
            total_score=team.total_score,
            participants=[
                ParticipantOut.from_orm_with_skills(p) for p in team.participants
            ],
        )


# ══════════════════════════════════════════════════════════════════════════════
# Session
# ══════════════════════════════════════════════════════════════════════════════

class SessionIn(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=["Хакатон 2026"])
    team_count: int = Field(ge=2, le=20, examples=[4])
    min_team_size: int = Field(ge=1, default=1, examples=[2])
    max_team_size: int = Field(ge=1, default=50, examples=[6])

    @field_validator("max_team_size")
    @classmethod
    def max_gte_min(cls, v: int, info) -> int:
        min_size = info.data.get("min_team_size", 1)
        if v < min_size:
            raise ValueError("max_team_size має бути ≥ min_team_size")
        return v


class SessionOut(BaseModel):
    id: uuid.UUID
    name: str
    team_count: int
    min_team_size: int
    max_team_size: int
    status: str
    # Токен повертається лише при створенні — потім не відображається
    organizer_token: str | None = None
    participants: list[ParticipantOut] = Field(default_factory=list)
    teams: list[TeamOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_full(cls, session, include_token: bool = False) -> "SessionOut":
        return cls(
            id=session.id,
            name=session.name,
            team_count=session.team_count,
            min_team_size=session.min_team_size,
            max_team_size=session.max_team_size,
            status=session.status.value,
            organizer_token=session.organizer_token if include_token else None,
            participants=[
                ParticipantOut.from_orm_with_skills(p)
                for p in session.participants
            ],
            teams=[TeamOut.from_orm_full(t) for t in session.teams],
        )


# ══════════════════════════════════════════════════════════════════════════════
# Distribution
# ══════════════════════════════════════════════════════════════════════════════

class DistributeIn(BaseModel):
    use_compatibility: bool = True
    balance_threshold: float = Field(default=0.15, ge=0.0, le=1.0)


class MoveParticipantIn(BaseModel):
    participant_id: uuid.UUID
    target_team_id: uuid.UUID


# ══════════════════════════════════════════════════════════════════════════════
# Generic responses
# ══════════════════════════════════════════════════════════════════════════════

class MessageOut(BaseModel):
    message: str


class ImportResultOut(BaseModel):
    imported: int
    message: str
