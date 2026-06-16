"""Superuser SQLAlchemy session for the admin dashboard.

We mount a second AsyncEngine on the alembic / superuser DSN so admin
queries run with BYPASSRLS — the API role (``coachito_api``) is locked
to per-tenant RLS via policies, but the operator dashboard needs to read
across tenants.  The engine is built lazily so plain API requests (which
never touch admin code) don't pay the connection-pool cost.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings

_admin_engine = None
_admin_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _dsn() -> str:
    raw = settings.alembic_database_url or settings.database_url
    # alembic_database_url may be the sync libpq form; normalise to asyncpg.
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw


def _get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _admin_engine, _admin_sessionmaker
    if _admin_sessionmaker is None:
        _admin_engine = create_async_engine(
            _dsn(),
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=4,
        )
        _admin_sessionmaker = async_sessionmaker(
            bind=_admin_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _admin_sessionmaker


async def get_admin_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session bound to the superuser engine — RLS-free.
    Reserved for ``/admin/*`` endpoints; do NOT use anywhere else."""
    async with _get_sessionmaker()() as session:
        yield session
