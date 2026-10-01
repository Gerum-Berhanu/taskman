"""Reusable named rate-limit dependency for route and router policies."""

from fastapi import Depends, HTTPException, Request

from app.core.config import settings
from app.core.rate_limit_policies import get_rate_limit_policy
from app.http.rate_limit import evaluate_rate_limit


class RateLimit:
    """FastAPI dependency callable that enforces one named policy."""

    def __init__(self, policy_name: str) -> None:
        self.policy_name = policy_name
        self.__rate_limit_policy_name__ = policy_name

    async def __call__(self, request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        policy = get_rate_limit_policy(self.policy_name)
        violation = await evaluate_rate_limit(request, policy)
        if violation is None:
            return
        raise HTTPException(
            status_code=violation.status_code,
            detail=violation.detail,
            headers=violation.headers,
        )


def rate_limit(policy_name: str) -> Depends:
    """Build a dependency marker for a named policy."""
    return Depends(RateLimit(policy_name))
