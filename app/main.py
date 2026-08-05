"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.routers import auth, workspaces, tasks

app = FastAPI(title="Taskman", version="0.1.0")
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(tasks.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
