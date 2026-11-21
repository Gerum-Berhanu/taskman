"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel.sql.expression import select

from app.api import auth, tasks, workspaces
from app.core.config import settings
from app.dependencies import SessionDep
from app.exceptions import ServiceUnavailableError, register_exception_handlers
from app.middleware.registry import register_middlewares
from app.infrastructure.database.session import engine
from app.infrastructure.redis.client import rc
from app.observability.setup import setup_logging


setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await rc.init_all_fail_open()
    yield
    await rc.close_all()  # already no-ops if _client is None
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
    **settings.docs_kwargs,
)
register_exception_handlers(app)
register_middlewares(app)
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(tasks.router)


@app.get("/health")
async def health(session: SessionDep) -> dict[str, str]:
    try:
        await session.exec(select(1))
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError from exc
    return {"status": "ok"}
