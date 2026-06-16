"""Unit tests for the AI draft-summary module.

No real network: we use a stubbed httpx MockTransport so the same code path
runs but Gemini's response is whatever the test wants.  Tests assert on
prompt assembly, locale routing, style routing, and error mapping — the HTTP
surface lives separately in tests/test_assessment_draft.py.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from src.ai.draft_summary import draft_assessment_summary
from src.ai.gemini_client import GeminiError
from src.config import settings


def _ok_response(text: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "candidates": [
                {"content": {"parts": [{"text": text}]}}
            ]
        },
    )


def _make_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")


SAMPLE_SKILLS = [
    {"name": "Forehand Drive", "score": 4, "note": None},
    {"name": "Bandeja", "score": 2, "note": "Late preparation."},
]


@pytest.mark.parametrize("style", ["encouraging", "direct", "warm"])
async def test_each_style_returns_text(style: str) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        captured["api_key"] = request.headers.get("x-goog-api-key")
        return _ok_response(f"draft for {style}")

    async with _make_client(handler) as http:
        out = await draft_assessment_summary(
            trainee_first_name="Andi",
            locale="en",
            style=style,  # type: ignore[arg-type]
            focuses=["groundstrokes"],
            skills=SAMPLE_SKILLS,  # type: ignore[arg-type]
            http=http,
        )
    assert out == f"draft for {style}"
    assert captured["api_key"] == "test-key"
    sys_text = captured["body"]["system_instruction"]["parts"][0]["text"]
    # Voice fragment carries through; locale label is English.
    assert "English" in sys_text
    if style == "direct":
        assert "Clinical" in sys_text
    elif style == "warm":
        assert "Friendly" in sys_text or "warm" in sys_text.lower()


async def test_indonesian_locale_uses_id_prompt() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        seen["sys"] = body["system_instruction"]["parts"][0]["text"]
        return _ok_response("draf dalam Bahasa Indonesia")

    async with _make_client(handler) as http:
        out = await draft_assessment_summary(
            trainee_first_name="Budi",
            locale="id",
            style="warm",
            focuses=[],
            skills=SAMPLE_SKILLS,  # type: ignore[arg-type]
            http=http,
        )
    assert "Indonesian" in seen["sys"]
    assert "Indonesia" in seen["sys"]
    assert out


async def test_user_prompt_includes_skills_and_notes() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        seen["user"] = body["contents"][0]["parts"][0]["text"]
        return _ok_response("ok")

    async with _make_client(handler) as http:
        await draft_assessment_summary(
            trainee_first_name="Andi",
            locale="en",
            style="encouraging",
            focuses=["groundstrokes", "net play"],
            skills=SAMPLE_SKILLS,  # type: ignore[arg-type]
            http=http,
        )
    text = seen["user"]
    assert "Andi" in text
    assert "groundstrokes, net play" in text
    assert "Forehand Drive: 4/5" in text
    assert "Bandeja: 2/5" in text
    assert "Late preparation." in text


async def test_empty_focuses_falls_back_to_general_practice() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        seen["user"] = body["contents"][0]["parts"][0]["text"]
        return _ok_response("ok")

    async with _make_client(handler) as http:
        await draft_assessment_summary(
            trainee_first_name="Andi",
            locale="en",
            style="encouraging",
            focuses=[],
            skills=SAMPLE_SKILLS,  # type: ignore[arg-type]
            http=http,
        )
    assert "general practice" in seen["user"]


async def test_5xx_raises_gemini_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="upstream overloaded")

    async with _make_client(handler) as http:
        with pytest.raises(GeminiError) as ex:
            await draft_assessment_summary(
                trainee_first_name="Andi",
                locale="en",
                style="encouraging",
                focuses=[],
                skills=SAMPLE_SKILLS,  # type: ignore[arg-type]
                http=http,
            )
    assert ex.value.status_code == 503


async def test_missing_api_key_raises_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "")

    def handler(_request: httpx.Request) -> httpx.Response:
        return _ok_response("never called")

    async with _make_client(handler) as http:
        with pytest.raises(RuntimeError):
            await draft_assessment_summary(
                trainee_first_name="Andi",
                locale="en",
                style="encouraging",
                focuses=[],
                skills=SAMPLE_SKILLS,  # type: ignore[arg-type]
                http=http,
            )


async def test_strips_markdown_code_fence() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return _ok_response("```\nclean prose here.\n```")

    async with _make_client(handler) as http:
        out = await draft_assessment_summary(
            trainee_first_name="Andi",
            locale="en",
            style="encouraging",
            focuses=[],
            skills=SAMPLE_SKILLS,  # type: ignore[arg-type]
            http=http,
        )
    assert out == "clean prose here."
