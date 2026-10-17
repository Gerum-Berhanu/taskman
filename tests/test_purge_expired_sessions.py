"""Purge expired client sessions (repo delete + CASCADE)."""

import asyncio
from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import select

from app.core.timeutils import utcnow
from app.dto.repository import (
    ClientSessionCreateData,
    RefreshTokenCreateData,
    UserCreateData,
)
from app.main import app
from app.models import ClientSession, RefreshToken
from app.repositories.unit_of_work import UnitOfWork


async def _seed_expired_and_live() -> tuple[object, object, object, object]:
    """Create one expired and one live session (each with a refresh token)."""
    session_factory = app.state.test_session_factory
    async with session_factory() as session:
        async with UnitOfWork(session) as uow:
            user = await uow.users.create(
                UserCreateData(
                    email="purge@example.com",
                    hashed_password="not-used",
                )
            )
            expired = await uow.client_sessions.create(
                ClientSessionCreateData(user_id=user.id)
            )
            live = await uow.client_sessions.create(
                ClientSessionCreateData(user_id=user.id)
            )

            expired_token = await uow.refresh_tokens.create(
                RefreshTokenCreateData(
                    client_session_id=expired.id,
                    token_hash=f"expired-{uuid4()}",
                )
            )
            live_token = await uow.refresh_tokens.create(
                RefreshTokenCreateData(
                    client_session_id=live.id,
                    token_hash=f"live-{uuid4()}",
                )
            )
            await uow.client_sessions.set_active_token_id(
                client_id=expired.id,
                token_id=expired_token.id,
            )
            await uow.client_sessions.set_active_token_id(
                client_id=live.id,
                token_id=live_token.id,
            )

            orm_expired = await session.get(ClientSession, expired.id)
            assert orm_expired is not None
            orm_expired.expires_at = utcnow() - timedelta(seconds=1)
            session.add(orm_expired)
            await session.flush()

            return expired.id, expired_token.id, live.id, live_token.id


async def _purge_expired() -> int:
    session_factory = app.state.test_session_factory
    async with session_factory() as session:
        async with UnitOfWork(session) as uow:
            return await uow.client_sessions.delete_expired()


async def _exists(model: type, identity: object) -> bool:
    session_factory = app.state.test_session_factory
    async with session_factory() as session:
        return await session.get(model, identity) is not None


async def _refresh_token_count_for_session(session_id: object) -> int:
    session_factory = app.state.test_session_factory
    async with session_factory() as session:
        result = await session.exec(
            select(RefreshToken).where(RefreshToken.client_session_id == session_id)
        )
        return len(result.all())


def test_delete_expired_removes_expired_session_and_tokens_keeps_live(
    client: TestClient,
) -> None:
    expired_session_id, expired_token_id, live_session_id, live_token_id = asyncio.run(
        _seed_expired_and_live()
    )

    deleted = asyncio.run(_purge_expired())
    assert deleted == 1

    assert asyncio.run(_exists(ClientSession, expired_session_id)) is False
    assert asyncio.run(_exists(RefreshToken, expired_token_id)) is False
    assert asyncio.run(_refresh_token_count_for_session(expired_session_id)) == 0

    assert asyncio.run(_exists(ClientSession, live_session_id)) is True
    assert asyncio.run(_exists(RefreshToken, live_token_id)) is True
