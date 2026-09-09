"""Auth HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from app.core.exceptions import InvalidCredentialsError
from app.repositories.user import UserRecord
from app.deps import AuthServiceDep, CurrentUserDep, UserServiceDep
from app.schemas.auth import LoginCredentials, RefreshTokenPayload, Token, UserCreateResponse
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserCreateResponse, status_code=HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate, user_service: UserServiceDep
) -> UserCreateResponse:
    user = await user_service.register(user_in)
    return UserCreateResponse(id=user["id"], email=user["email"])


@router.post("/login", response_model=Token)
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthServiceDep,
) -> Token:
    try:
        valid_form = LoginCredentials(
            email=form_data.username,
            password=form_data.password,
        )
    except ValidationError as exc:
        raise InvalidCredentialsError from exc
        # raise InvalidCredentialsError, but record the original ValidationError (exc) as its cause.

    return await auth_service.login(valid_form.email, valid_form.password)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_payload: RefreshTokenPayload, 
    auth_service: AuthServiceDep
) -> Token:
    token = refresh_payload.refresh_token
    return await auth_service.refresh(token)


@router.post("/logout", status_code=HTTP_204_NO_CONTENT)
async def logout_user(
    refresh_payload: RefreshTokenPayload,
    auth_service: AuthServiceDep
) -> None:
    token = refresh_payload.refresh_token
    await auth_service.logout(token)


@router.post("/logout-all", status_code=HTTP_204_NO_CONTENT)
async def logout_all_sessions(
    user: CurrentUserDep,
    auth_service: AuthServiceDep,
) -> None:
    await auth_service.logout_all(user["id"])


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUserDep) -> UserRecord:
    return user
