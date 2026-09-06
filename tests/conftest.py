import asyncio
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import app.models  # noqa: F401 — register User, Task, UserSession on metadata
from app.database.unit_of_work import UnitOfWork
from app.deps import get_uow
from app.main import app


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    test_engine = create_async_engine(database_url, poolclass=NullPool)
    test_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def create_tables() -> None:
        async with test_engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)

    asyncio.run(create_tables())

    async def override_get_uow() -> AsyncGenerator[UnitOfWork, None]:
        async with test_session_factory() as session:
            async with UnitOfWork(session) as uow:
                yield uow

    app.dependency_overrides[get_uow] = override_get_uow
    # Shared with tests that need direct DB setup (e.g. deactivate a user).
    app.state.test_session_factory = test_session_factory

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        if hasattr(app.state, "test_session_factory"):
            delattr(app.state, "test_session_factory")
        asyncio.run(test_engine.dispose())


async def _set_user_active(user_id: UUID, *, is_active: bool) -> None:
    session_factory = app.state.test_session_factory
    async with session_factory() as session:
        async with UnitOfWork(session) as uow:
            updated = await uow.users.set_is_active(user_id, is_active=is_active)
            assert updated is not None


def deactivate_user(user_id: UUID) -> None:
    asyncio.run(_set_user_active(user_id, is_active=False))


async def _used_history_len(family_id: UUID) -> int:
    session_factory = app.state.test_session_factory
    async with session_factory() as session:
        async with UnitOfWork(session) as uow:
            family = await uow.user_sessions.get(family_id)
            assert family is not None
            return len(family["used_token_hashes"])


def used_history_len(family_id: UUID) -> int:
    return asyncio.run(_used_history_len(family_id))
