"""Auth HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from app.core.exceptions import EmailAlreadyRegisteredError
from app.database.records import UserRecord
from app.deps import AuthServiceDep, CurrentUserDep, UserServiceDep
from app.models.user import Token, UserAuthenticate, UserCreate, UserCreateResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserCreateResponse, status_code=HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate, user_service: UserServiceDep
) -> UserCreateResponse:
    try:
        user = user_service.register(user_in)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Account with this email already exists",
        )

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
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(data={"sub": valid_form.email})
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUserDep) -> UserRecord:
    return user
