import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

_skill_category = Enum("technical", "tactical", "physical", "mental", name="skill_category", create_type=False)


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("sport_id", "workspace_id", "code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sport_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sports.id"), nullable=False)
    curriculum_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(_skill_category, nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    name_id: Mapped[str] = mapped_column(String(120), nullable=False)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class SkillLevelDescriptor(Base):
    __tablename__ = "skill_level_descriptors"
    __table_args__ = (UniqueConstraint("skill_id", "workspace_id", "level"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    description_en: Mapped[str] = mapped_column(Text, nullable=False)
    description_id: Mapped[str] = mapped_column(Text, nullable=False)
