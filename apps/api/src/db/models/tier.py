import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Tier(Base):
    __tablename__ = "tiers"
    __table_args__ = (UniqueConstraint("curriculum_id", "workspace_id", "code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sport_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sports.id"), nullable=False)
    curriculum_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name_game_en: Mapped[str] = mapped_column(String(50), nullable=False)
    name_game_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name_skill_en: Mapped[str] = mapped_column(String(50), nullable=False)
    name_skill_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name_custom_en: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name_custom_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    icon_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class TierRequirement(Base):
    __tablename__ = "tier_requirements"
    __table_args__ = (UniqueConstraint("tier_id", "skill_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tiers.id", ondelete="CASCADE"), nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    min_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
