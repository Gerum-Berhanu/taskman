"""Tasks HTTP endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/tasks", tags=["tasks"])
