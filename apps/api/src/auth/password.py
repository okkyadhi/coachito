"""Password hashing + verify + brute-force rate limiting.

argon2-cffi with the library's default parameters — OWASP-recommended and
calibrated to take ~50ms on a modern x86 box.  Hashes are stored in the
PHC string format so we can rotate parameters without a re-encode.

Rate limiting: Redis-backed bucket keyed on the email.  Six failed
attempts in 15 minutes raises ``RateLimitedError`` (429).  Successful
login clears the bucket so a typo-prone return user isn't punished.
"""

from __future__ import annotations

import logging
import re
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from redis.asyncio import Redis

log = logging.getLogger(__name__)

# Single shared hasher — instantiating is cheap but pointless to repeat.
_hasher: Final[PasswordHasher] = PasswordHasher()

# OWASP ASVS-friendly minimum.  No max length (argon2 handles arbitrary
# strings; setting one introduces a DoS / truncation footgun).
MIN_LENGTH: Final[int] = 8

# Bucket settings.
_LIMIT_ATTEMPTS: Final[int] = 6
_LIMIT_WINDOW_SECONDS: Final[int] = 15 * 60


class RateLimitedError(Exception):
    """Raised when too many failed attempts have been recorded for an email."""


class WeakPasswordError(Exception):
    """Raised by ``hash_password`` for inputs that don't meet ``MIN_LENGTH``
    or look obviously bad (whitespace-only).  Wider policy lives at the
    schema level."""


# ── Hash / verify ───────────────────────────────────────────────


def hash_password(plain: str) -> str:
    if not plain or len(plain) < MIN_LENGTH:
        raise WeakPasswordError(
            f"Password must be at least {MIN_LENGTH} characters."
        )
    if re.fullmatch(r"\s+", plain):
        raise WeakPasswordError("Password cannot be only whitespace.")
    return _hasher.hash(plain)


def verify_password(plain: str, stored_hash: str | None) -> bool:
    """Constant-time-ish check.  Always runs the hasher even when the user
    has no password set, so an attacker can't time-distinguish "no such
    account" from "wrong password"."""
    if not stored_hash:
        # Dummy verify with a constant valid hash to keep timing consistent.
        try:
            _hasher.verify(_DUMMY_HASH, plain)
        except VerifyMismatchError:
            pass
        return False
    try:
        return _hasher.verify(stored_hash, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(stored_hash)
    except InvalidHashError:
        return True


# Constant hash so we always have something to verify against when the user
# has no password.  Value doesn't matter — it'll never match anything.
_DUMMY_HASH: Final[str] = _hasher.hash("not-a-real-password-just-for-timing")


# ── Rate limit ──────────────────────────────────────────────────


def _bucket_key(email: str) -> str:
    return f"auth:pwlogin:fails:{email.strip().lower()}"


async def check_rate_limit(redis: Redis, *, email: str) -> None:
    raw = await redis.get(_bucket_key(email))
    if raw is None:
        return
    try:
        count = int(raw)
    except (TypeError, ValueError):
        return
    if count >= _LIMIT_ATTEMPTS:
        raise RateLimitedError(email)


async def record_failure(redis: Redis, *, email: str) -> None:
    key = _bucket_key(email)
    pipe = redis.pipeline()
    pipe.incr(key, 1)
    pipe.expire(key, _LIMIT_WINDOW_SECONDS)
    await pipe.execute()


async def clear_attempts(redis: Redis, *, email: str) -> None:
    await redis.delete(_bucket_key(email))
