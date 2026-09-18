import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import app.models  # noqa: F401 — register models on metadata
from app.core.security import hash_refresh_token
from app.core.timeutils import utcnow
from app.database.unit_of_work import UnitOfWork
from app.deps import get_uow
from app.main import app
from app.models import ClientSession


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    test_engine = create_async_engine(database_url, poolclass=NullPool)

    @event.listens_for(test_engine.sync_engine, "connect")
    def _set_sqlite_fk(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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


def activate_user(user_id: UUID) -> None:
    asyncio.run(_set_user_active(user_id, is_active=True))


async def _expire_session_for_refresh(refresh_token: str) -> None:
    session_factory = app.state.test_session_factory
    async with session_factory() as session:
        async with UnitOfWork(session) as uow:
            row = await uow.refresh_tokens.get_by_token_hash(
                hash_refresh_token(refresh_token)
            )
            assert row is not None
            client_session = await session.get(ClientSession, row.client_session_id)
            assert client_session is not None
            client_session.expires_at = utcnow() - timedelta(seconds=1)
            session.add(client_session)
            await session.flush()


def expire_session_for_refresh(refresh_token: str) -> None:
    asyncio.run(_expire_session_for_refresh(refresh_token))
