"""log_event after_commit: emit only after a successful UoW commit."""

import asyncio
from logging import INFO, getLogger

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.observability.events.domain import TASK_CREATED, TASK_UPDATED
from app.observability.log_event import log_event
from app.repositories.unit_of_work import UnitOfWork


logger = getLogger(__name__)


async def _queue_deferred_then_commit() -> None:
    session_factory = app.state.test_session_factory
    async with session_factory() as session:
        async with UnitOfWork(session) as uow:
            log_event(
                logger,
                INFO,
                TASK_CREATED,
                after_commit=uow,
                task_id="t-commit",
            )


async def _queue_deferred_then_rollback() -> None:
    session_factory = app.state.test_session_factory
    async with session_factory() as session:
        async with UnitOfWork(session) as uow:
            log_event(
                logger,
                INFO,
                TASK_CREATED,
                after_commit=uow,
                task_id="t-rollback",
            )
            raise RuntimeError("force rollback")


async def _immediate_and_deferred_then_rollback() -> None:
    session_factory = app.state.test_session_factory
    async with session_factory() as session:
        async with UnitOfWork(session) as uow:
            log_event(logger, INFO, TASK_UPDATED, task_id="t-immediate")
            log_event(
                logger,
                INFO,
                TASK_CREATED,
                after_commit=uow,
                task_id="t-deferred",
            )
            raise RuntimeError("force rollback")


def test_log_event_after_commit_emits_on_successful_commit(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(INFO, logger=__name__):
        asyncio.run(_queue_deferred_then_commit())

    matches = [r for r in caplog.records if TASK_CREATED in r.message]
    assert len(matches) == 1
    assert "task_id=t-commit" in matches[0].message


def test_log_event_after_commit_skips_on_rollback(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(INFO, logger=__name__):
        with pytest.raises(RuntimeError, match="force rollback"):
            asyncio.run(_queue_deferred_then_rollback())

    assert not any(TASK_CREATED in r.message for r in caplog.records)


def test_immediate_log_event_still_emits_when_uow_rolls_back(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(INFO, logger=__name__):
        with pytest.raises(RuntimeError, match="force rollback"):
            asyncio.run(_immediate_and_deferred_then_rollback())

    assert any(TASK_UPDATED in r.message for r in caplog.records)
    assert not any(TASK_CREATED in r.message for r in caplog.records)
