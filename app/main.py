"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from sqlmodel.sql.expression import select

from app.api.v1 import auth, tasks, workspaces, workspace_members
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.exceptions import FailedDatabaseConnection
from app.core.log import setup_logging
from app.core.middleware_registrar import register_middlewares
from app.database.session import engine
from app.deps import SessionDep


setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name, 
    version="0.1.0", 
    debug=settings.debug,
    lifespan=lifespan
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
