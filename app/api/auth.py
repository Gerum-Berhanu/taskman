"""Auth HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from app.api.helpers.auth_cookies import (
    RefreshTokenCookie,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from app.exceptions import InvalidCredentialsError, InvalidTokenError
from app.dependencies import (
    AuthLoginLimit,
    AuthLogoutLimit,
    AuthRefreshLimit,
    AuthRegisterLimit,
    AuthServiceDep,
    CurrentUserDep,
    DomainReadLimit,
    UserServiceDep,
)
from app.dto.api.auth import AccessTokenResponse, LoginCredentials, UserCreateResponse
from app.dto.api.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserCreateResponse,
    status_code=HTTP_201_CREATED,
    dependencies=[AuthRegisterLimit],
)
async def register_user(
    payload: UserCreate, user_service: UserServiceDep, bg_tasks: BackgroundTasks
) -> UserCreateResponse:
    user = await user_service.register(payload, bg_tasks)
    return UserCreateResponse(id=user.id, email=user.email)


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    dependencies=[AuthLoginLimit],
)
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthServiceDep,
    response: Response,
) -> AccessTokenResponse:
    try:
        valid_form = LoginCredentials(
            email=form_data.username,
            password=form_data.password,
        )
    except ValidationError as exc:
        raise InvalidCredentialsError from exc
        # raise InvalidCredentialsError, but record the original ValidationError (exc) as its cause.

    access, refresh = await auth_service.login(valid_form.email, valid_form.password)
    set_refresh_cookie(response, refresh)
    return AccessTokenResponse(access_token=access)


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    dependencies=[AuthRefreshLimit],
)
async def refresh_token(
    response: Response,
    auth_service: AuthServiceDep,
    refresh_token: RefreshTokenCookie = None,
) -> AccessTokenResponse:
    if not refresh_token:
        raise InvalidTokenError
    access, new_refresh = await auth_service.refresh(refresh_token)
    set_refresh_cookie(response, new_refresh)
    return AccessTokenResponse(access_token=access)


@router.post(
    "/logout",
    status_code=HTTP_204_NO_CONTENT,
    dependencies=[AuthLogoutLimit],
)
async def logout_user(
    response: Response,
    auth_service: AuthServiceDep,
    refresh_token: RefreshTokenCookie = None,
) -> None:
    if not refresh_token:
        raise InvalidTokenError
    await auth_service.logout(refresh_token)
    clear_refresh_cookie(response)


@router.post(
    "/logout-all",
    status_code=HTTP_204_NO_CONTENT,
    dependencies=[AuthLogoutLimit],
)
async def logout_all_sessions(
    response: Response,
    auth_service: AuthServiceDep,
    refresh_token: RefreshTokenCookie = None,
) -> None:
    if not refresh_token:
        raise InvalidTokenError
    await auth_service.logout_all_user_sessions(refresh_token)
    clear_refresh_cookie(response)


@router.get("/me", response_model=UserRead, dependencies=[DomainReadLimit])
async def get_me(current_user: CurrentUserDep) -> UserRead:
    return current_user
