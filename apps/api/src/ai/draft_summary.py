"""Draft an assessment summary from structured skill scores.

Pure-Python orchestrator: takes the assessment payload + style + locale and
calls Gemini.  The HTTP layer (``src.assessments.draft_router``) handles
authn, payload assembly from the DB, and audit logging.
"""

from __future__ import annotations

from typing import Literal, TypedDict

import httpx

from .gemini_client import generate_text
from .prompts import summary_en, summary_id

SummaryStyle = Literal["encouraging", "direct", "warm"]
SummaryLocale = Literal["en", "id"]

_VALID_STYLES: tuple[SummaryStyle, ...] = ("encouraging", "direct", "warm")
_MAX_SKILLS = 30  # 27 is the real cap; small buffer for safety


class SkillInput(TypedDict):
    """Single row for the prompt's skill table.

    ``note`` is the coach's optional free-text comment for that skill —
    when present, it's included verbatim so the draft can pick up specifics.
    """

    name: str
    score: int
    note: str | None


def _build_user_prompt(
    *,
    trainee_first_name: str,
    focuses: list[str],
    skills: list[SkillInput],
) -> str:
    focuses_line = (
        ", ".join(focuses) if focuses else "general practice"
    )
    lines = [
        f"Trainee: {trainee_first_name}",
        f"Session focuses: {focuses_line}",
        "Skills assessed:",
    ]
    for s in skills[:_MAX_SKILLS]:
        suffix = f"  {s['note'].strip()}" if s.get("note") else ""
        lines.append(f"- {s['name']}: {int(s['score'])}/5{suffix}")
    return "\n".join(lines)


def _strip_wrapper(text: str) -> str:
    """Trim accidental markdown code fences the model may emit despite
    response_mime_type=text/plain."""
    out = text.strip()
    if out.startswith("```"):
        # Drop fence + optional language tag on first line.
        nl = out.find("\n")
        if nl != -1:
            out = out[nl + 1:]
        if out.endswith("```"):
            out = out[: -3]
    return out.strip()


async def draft_assessment_summary(
    *,
    trainee_first_name: str,
    locale: SummaryLocale,
    style: SummaryStyle,
    focuses: list[str],
    skills: list[SkillInput],
    http: httpx.AsyncClient,
) -> str:
    """Build the prompt + call Gemini + return the cleaned summary.

    Raises ``RuntimeError`` when ``GEMINI_API_KEY`` is unset (router maps to
    503) and ``GeminiError`` on upstream failure (router maps to 502).
    """
    if style not in _VALID_STYLES:
        style = "encouraging"
    prompt_module = summary_id if locale == "id" else summary_en
    system_instruction = prompt_module.build_system_prompt(style)
    user_prompt = _build_user_prompt(
        trainee_first_name=trainee_first_name,
        focuses=focuses,
        skills=skills,
    )
    raw = await generate_text(
        http=http,
        system_instruction=system_instruction,
        user_prompt=user_prompt,
    )
    return _strip_wrapper(raw)


__all__ = [
    "SkillInput",
    "SummaryLocale",
    "SummaryStyle",
    "draft_assessment_summary",
]
