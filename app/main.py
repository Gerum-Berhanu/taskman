"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.v1 import auth, tasks, workspaces, workspace_members
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.database.session import engine


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
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(workspace_members.router)
app.include_router(tasks.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
