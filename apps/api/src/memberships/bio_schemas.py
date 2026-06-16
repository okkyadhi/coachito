"""Pydantic shape for the membership.bio JSONB blob.

Used both on read (so the FE always sees a normalized object) and on write
(future PATCH coach-self-edit, not in this revamp).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CertificationOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    issuer: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    year: int = Field(ge=1900, le=2100)


class CoachBio(BaseModel):
    """All fields optional — coaches choose what to show."""

    model_config = ConfigDict(extra="forbid")

    headline: str | None = Field(default=None, max_length=120)
    about: str | None = Field(default=None, max_length=1500)
    years_coaching: int | None = Field(default=None, ge=0, le=80)
    certifications: list[CertificationOut] = Field(default_factory=list, max_length=10)
    languages: list[str] = Field(default_factory=list, max_length=10)
    specialties: list[str] = Field(default_factory=list, max_length=12)
    photo_url: str | None = None


def coerce_bio(raw: object) -> CoachBio:
    """Tolerant parse — invalid shapes degrade to empty rather than 500."""
    if not isinstance(raw, dict):
        return CoachBio()
    try:
        return CoachBio.model_validate(raw)
    except Exception:
        return CoachBio()
