"""JWT encode/decode for access + refresh tokens (HS256)."""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

import jwt

from src.config import settings

TokenType = Literal["access", "refresh"]


def _ttl(token_type: TokenType) -> timedelta:
    if token_type == "access":
        return timedelta(minutes=settings.jwt_access_ttl_minutes)
    return timedelta(days=settings.jwt_refresh_ttl_days)


def encode_token(
    *,
    user_id: UUID,
    workspace_id: UUID | None,
    token_type: TokenType,
    jti: str | None = None,
) -> tuple[str, str, datetime]:
    """Returns (encoded_jwt, jti, expires_at_utc)."""
    now = datetime.now(UTC)
    exp = now + _ttl(token_type)
    jti_value = jti or str(uuid4())
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "wsid": str(workspace_id) if workspace_id else None,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": jti_value,
    }
    encoded = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return encoded, jti_value, exp


def decode_token(token: str) -> dict[str, Any]:
    """Raises jwt.PyJWTError on failure (expired, bad signature, etc.)."""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


class TokenPairOut:
    """Plain bag of values used when assembling the response schema."""

    def __init__(
        self,
        *,
        access_token: str,
        refresh_token: str,
        refresh_jti: str,
        refresh_exp: datetime,
        expires_in: int,
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.refresh_jti = refresh_jti
        self.refresh_exp = refresh_exp
        self.expires_in = expires_in


def issue_token_pair(user_id: UUID, workspace_id: UUID | None = None) -> TokenPairOut:
    access_token, _, _ = encode_token(
        user_id=user_id, workspace_id=workspace_id, token_type="access"
    )
    refresh_token, refresh_jti, refresh_exp = encode_token(
        user_id=user_id, workspace_id=workspace_id, token_type="refresh"
    )
    return TokenPairOut(
        access_token=access_token,
        refresh_token=refresh_token,
        refresh_jti=refresh_jti,
        refresh_exp=refresh_exp,
        expires_in=settings.jwt_access_ttl_minutes * 60,
    )
