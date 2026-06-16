"""Thin HTTP wrapper around Gemini's generateContent endpoint.

No business logic — just the request shape, auth, and error normalisation.
``draft_summary`` builds the prompt; this module turns it into bytes on the wire.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from src.config import settings

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiError(RuntimeError):
    """Raised when Gemini returns a non-2xx, or when the response is missing
    the text candidate.  Includes the upstream status + body for logging; the
    HTTP layer wraps this in a generic 502 so we never leak upstream bodies
    to the FE."""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"Gemini error {status_code}: {body[:200]}")
        self.status_code = status_code
        self.body = body


@dataclass(frozen=True)
class GenerationConfig:
    temperature: float = 0.6
    # ~1 token ≈ 0.75 words, so 800 tokens fits the 500-word ceiling with
    # headroom for closing punctuation + the occasional run-over.
    max_output_tokens: int = 800
    response_mime_type: str = "text/plain"


async def generate_text(
    *,
    http: httpx.AsyncClient,
    system_instruction: str,
    user_prompt: str,
    config: GenerationConfig | None = None,
) -> str:
    """One-shot text generation.  Returns the model's text output, trimmed.

    Raises ``RuntimeError`` if the API key is unset (caller deals with the
    503 response shape) and ``GeminiError`` on any other failure path.
    """
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")

    cfg = config or GenerationConfig()
    url = f"{_BASE_URL}/{settings.gemini_model}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [
            {"role": "user", "parts": [{"text": user_prompt}]},
        ],
        "generationConfig": {
            "temperature": cfg.temperature,
            "maxOutputTokens": cfg.max_output_tokens,
            "responseMimeType": cfg.response_mime_type,
        },
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": settings.gemini_api_key,
    }

    try:
        resp = await http.post(
            url,
            content=json.dumps(payload),
            headers=headers,
            timeout=settings.gemini_timeout_s,
        )
    except httpx.HTTPError as e:
        raise GeminiError(0, f"network error: {e!s}") from e

    if resp.status_code >= 400:
        raise GeminiError(resp.status_code, resp.text)

    try:
        data = resp.json()
        # candidates[0].content.parts[0].text — Gemini's standard shape.
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, ValueError) as e:
        raise GeminiError(resp.status_code, f"unexpected shape: {resp.text[:200]}") from e

    return str(text).strip()
