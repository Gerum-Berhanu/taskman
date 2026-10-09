"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel.sql.expression import select

from app.api.v1 import auth, tasks, workspaces, workspace_members
from app.core.config import settings
from app.core.exceptions import FailedDatabaseConnection
from app.deps import SessionDep
from app.exception_handlers import register_exception_handlers
from app.middleware.registry import register_middlewares
from app.infrastructure.database.session import engine
from app.infrastructure.redis.client import redis_client
from app.observability.setup import setup_logging


setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.init_redis_fail_open()
    yield
    await redis_client.close_redis()  # already no-ops if _client is None
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
app.include_router(workspace_members.router)
app.include_router(tasks.router)


@app.get("/health")
async def health(session: SessionDep) -> dict[str, str]:
    try:
        await session.exec(select(1))
    except Exception:
        raise FailedDatabaseConnection
    return {"status": "ok"}
