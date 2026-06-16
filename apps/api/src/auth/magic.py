"""Magic-link tokens stored in Redis as sha256(token) → email, 15min TTL.

The raw URL-safe token never touches the DB — only the hash is stored, so a
Redis-snapshot leak doesn't let an attacker mint sessions.  Consume is atomic
via GETDEL so the link is one-shot.
"""

import hashlib
import secrets
from datetime import timedelta

from redis.asyncio import Redis

MAGIC_LINK_TTL = timedelta(minutes=15)
PASSWORD_RESET_TTL = timedelta(minutes=30)
_KEY_PREFIX = "magic:"
_REFRESH_PREFIX = "refresh:"
_PWRESET_PREFIX = "pwreset:"


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ── Magic-link tokens ─────────────────────────────────────────────


async def store_magic_token(redis: Redis, token: str, email: str) -> None:
    key = f"{_KEY_PREFIX}{_hash(token)}"
    await redis.set(key, email, ex=int(MAGIC_LINK_TTL.total_seconds()))


async def consume_magic_token(redis: Redis, token: str) -> str | None:
    """Atomic one-shot read: returns email or None."""
    key = f"{_KEY_PREFIX}{_hash(token)}"
    value = await redis.getdel(key)
    if value is None:
        return None
    return value if isinstance(value, str) else value.decode("utf-8")


# ── Refresh-token jti registry (rotation) ────────────────────────


def _refresh_key(user_id: str, jti: str) -> str:
    return f"{_REFRESH_PREFIX}{user_id}:{jti}"


async def register_refresh_jti(
    redis: Redis, user_id: str, jti: str, ttl_seconds: int
) -> None:
    await redis.set(_refresh_key(user_id, jti), "1", ex=ttl_seconds)


async def revoke_and_check_refresh_jti(
    redis: Redis, user_id: str, jti: str
) -> bool:
    """Atomic: returns True if the jti existed (and has now been revoked)."""
    return await redis.getdel(_refresh_key(user_id, jti)) is not None


# ── Password-reset tokens ────────────────────────────────────────


async def store_password_reset_token(
    redis: Redis, token: str, email: str
) -> None:
    key = f"{_PWRESET_PREFIX}{_hash(token)}"
    await redis.set(key, email, ex=int(PASSWORD_RESET_TTL.total_seconds()))


async def consume_password_reset_token(
    redis: Redis, token: str
) -> str | None:
    """Atomic one-shot read: returns email or None.

    Mirrors ``consume_magic_token`` but with a separate Redis namespace so a
    magic-link token can't be replayed as a password reset (and vice-versa)."""
    key = f"{_PWRESET_PREFIX}{_hash(token)}"
    value = await redis.getdel(key)
    if value is None:
        return None
    return value if isinstance(value, str) else value.decode("utf-8")
