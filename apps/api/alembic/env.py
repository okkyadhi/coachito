import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic runs as superuser (ALEMBIC_DATABASE_URL); the API runtime uses
# the non-superuser coachito_api role from DATABASE_URL.
database_url = os.environ.get("ALEMBIC_DATABASE_URL") or os.environ.get("DATABASE_URL")
if database_url:
    # Same normalization as src/db/session.py — managed providers ship
    # plain postgresql:// URLs, our SQLAlchemy engines want the +asyncpg
    # driver suffix.
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://", "postgresql+asyncpg://", 1
        )
    config.set_main_option("sqlalchemy.url", database_url)

from src.db.base import Base
import src.db.models  # noqa: F401 — registers all ORM models with Base.metadata

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
