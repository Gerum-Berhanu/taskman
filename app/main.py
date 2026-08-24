"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.v1 import auth, tasks, workspaces
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.database.session import create_db_and_tables

setup_logging()

app = FastAPI(title=settings.app_name, version="0.1.0", debug=settings.debug)
register_exception_handlers(app)
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(tasks.router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
