"""Auth HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from starlette.status import HTTP_201_CREATED

from app.database.records import UserRecord
from app.deps import AuthServiceDep, CurrentUserDep, UserServiceDep
from app.schemas.user import Token, UserAuthenticate, UserCreate, UserCreateResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserCreateResponse, status_code=HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate, user_service: UserServiceDep
) -> UserCreateResponse:
    user = user_service.register(user_in)
    return UserCreateResponse(id=user["id"], email=user["email"])


@router.post("/login", response_model=Token)
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthServiceDep,
) -> Token:
    valid_form = UserAuthenticate(
        email=form_data.username,
        password=form_data.password,
    )

    user = auth_service.authenticate(valid_form.email, valid_form.password)
    access_token = auth_service.create_access_token(data={"sub": user["email"]})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUserDep) -> UserRecord:
    return user
