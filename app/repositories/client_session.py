"""Client session persistence."""

from datetime import timedelta
from uuid import UUID

from sqlalchemy import func
from sqlmodel import col, delete, select

from app.core.config import settings
from app.core.timeutils import utcnow
from app.models import ClientSession
from app.repositories.base import BaseRepository
from app.dto.repository import ClientSessionCreateData, ClientSessionRecord


class ClientSessionRepository(
    BaseRepository[ClientSession, ClientSessionRecord, ClientSessionCreateData]
):
    model = ClientSession
    record = ClientSessionRecord

    async def delete(self, session_id: UUID) -> int:
        result = await self._session.exec(
            delete(ClientSession).where(col(ClientSession.id) == session_id)
        )
        return result.rowcount or 0

    async def delete_all_user_sessions(self, user_id: UUID) -> int:
        """Delete every session for a user; return how many were deleted."""
        result = await self._session.exec(
            delete(ClientSession).where(col(ClientSession.user_id) == user_id)
        )
        return result.rowcount or 0

    async def delete_by_device(self, device_id: UUID) -> int:
        result = await self._session.exec(
            delete(ClientSession).where(col(ClientSession.device_id) == device_id)
        )
        return result.rowcount or 0

    async def delete_expired(self) -> int:
        result = await self._session.exec(
            delete(ClientSession).where(col(ClientSession.expires_at) <= utcnow())
        )
        return result.rowcount or 0

    async def make_room_for_login(self, user_id: UUID, *, max_sessions: int) -> int:
        """Drop least-active sessions so login can create one more (at most max_sessions)."""
        keep = max_sessions - 1
        activity = func.coalesce(ClientSession.rotated_at, ClientSession.created_at)
        result = await self._session.exec(
            select(ClientSession)
            .where(col(ClientSession.user_id) == user_id)
            .order_by(activity.asc(), col(ClientSession.id).asc())
        )
        rows = result.all()
        excess = rows[: max(0, len(rows) - keep)]
        for row in excess:
            await self._session.delete(row)
        if excess:
            await self._session.flush()
        return len(excess)

    async def list_by_user(self, user_id: UUID) -> list[ClientSessionRecord]:
        result = await self._session.exec(
            select(ClientSession)
            .where(col(ClientSession.user_id) == user_id)
            .order_by(
                col(ClientSession.created_at).desc(),
                col(ClientSession.rotated_at).desc(),
                col(ClientSession.id),
            )
        )
        return [self._to_record(session) for session in result.all()]

    async def set_active_token_id(
        self,
        *,
        client_id: UUID,
        token_id: UUID,
        is_rotation: bool = False,
    ) -> ClientSessionRecord | None:
        """Point the session at a refresh token; optionally bump rotation/expiry."""
        client_session = await self._session.get(ClientSession, client_id)
        if client_session is None:
            return None

        client_session.active_token_id = token_id
        if is_rotation:
            client_session.rotated_at = utcnow()
            client_session.expires_at = utcnow() + timedelta(
                minutes=settings.refresh_token_expire_minutes
            )

        await self._flush_refresh(client_session)
        return self._to_record(client_session)
