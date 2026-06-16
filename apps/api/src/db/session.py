import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_RAW_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://coachito:coachito@localhost:5433/coachito",
)
# Managed Postgres providers (Railway / Render / Heroku) hand out plain
# ``postgresql://...`` URLs; SQLAlchemy needs the driver suffix to pick
# asyncpg.  Do the swap here so the rest of the app stays unaware.
if _RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = _RAW_DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )
elif _RAW_DATABASE_URL.startswith("postgres://"):
    # Some providers (Heroku-era) still emit the deprecated ``postgres://``.
    DATABASE_URL = _RAW_DATABASE_URL.replace(
        "postgres://", "postgresql+asyncpg://", 1
    )
else:
    DATABASE_URL = _RAW_DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    # Recycle long-idle conns instead of paying a SELECT 1 roundtrip per
    # checkout — pre-ping adds 50–150 ms per request when DB is on a
    # different host.
    pool_recycle=1800,
    pool_pre_ping=False,
    echo=os.environ.get("ENVIRONMENT") == "development",
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
