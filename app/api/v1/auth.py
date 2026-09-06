"""Auth HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from starlette.status import HTTP_201_CREATED

from app.core.exceptions import InvalidCredentialsError
from app.repositories.records import UserRecord
from app.deps import AuthServiceDep, CurrentUserDep, UserServiceDep
from app.schemas.auth import LoginCredentials, Token, UserCreateResponse
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


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUserDep) -> UserRecord:
    return user
