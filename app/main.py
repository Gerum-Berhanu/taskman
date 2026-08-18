"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.v1 import auth, tasks, workspaces
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title=settings.app_name, version="0.1.0", debug=settings.debug)
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(tasks.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
