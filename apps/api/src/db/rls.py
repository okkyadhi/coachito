"""Workspace RLS context helpers.

Every request handler that accesses tenant-scoped tables must call
set_workspace_context() before any query.  FastAPI dependency:

    async def db_with_workspace(
        workspace_id: UUID,
        session: AsyncSession = Depends(get_session),
    ) -> AsyncGenerator[AsyncSession, None]:
        await set_workspace_context(session, workspace_id)
        yield session
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_workspace_context(session: AsyncSession, workspace_id: UUID) -> None:
    """SET LOCAL app.current_workspace_id for the current transaction."""
    await session.execute(
        text("SELECT set_config('app.current_workspace_id', :wid, TRUE)"),
        {"wid": str(workspace_id)},
    )


async def clear_workspace_context(session: AsyncSession) -> None:
    """Clear the workspace context (admin / seed operations)."""
    await session.execute(
        text("SELECT set_config('app.current_workspace_id', '', TRUE)")
    )
