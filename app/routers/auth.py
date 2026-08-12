"""Auth HTTP endpoints."""

from fastapi.security import OAuth2PasswordRequestForm
import jwt
from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import EmailStr
from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from app.config import settings
from app.schemas import Token, UserAuthenticate, UserCreate, UserCreateResponse
from app.security import get_dummy_hash, verify_password
from app.storage import UserStore, user_store
from app.timeutils import utcnow

router = APIRouter(prefix="/auth", tags=["auth"])

DUMMY_HASH = get_dummy_hash("my_dummy_password")


def get_user_store() -> UserStore:
    return user_store


UserStoreDep = Annotated[UserStore, Depends(get_user_store)]


@router.post("/register", response_model=UserCreateResponse, status_code=HTTP_201_CREATED)
async def register_user(user_in: UserCreate, storage: UserStoreDep) -> dict:
    if storage.get_by_email(user_in.email) is not None:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Account with this email already exists"
        )
    
    user = storage.create(user_in.model_dump())
    response_dict = {
        "id": user["id"],
        "email": user["email"],
        "message": "User registered successfully"
    }
    return response_dict


def authenticate_user(db: UserStore, email: EmailStr, password: str) -> dict | bool:
    user = db.get_by_email(email)
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()

    expire = utcnow()
    expire += (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        payload=to_encode,
        key=settings.secret_key,
        algorithm=settings.algorithm,
    )
    return encoded_jwt
    

@router.post("/login")
async def login_user(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], storage: UserStoreDep):
    valid_form = UserAuthenticate(
        email=form_data.username,
        password=form_data.password
    )

    user = authenticate_user(storage, valid_form.email, valid_form.password)
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token_data = {"sub": valid_form.email}
    access_token = create_access_token(data=token_data)
    return Token(access_token=access_token, token_type="bearer")