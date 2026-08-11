"""Auth HTTP endpoints."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from app.schemas import UserCreate, UserCreateResponse
from app.storage import UserStore, user_store

router = APIRouter(prefix="/auth", tags=["auth"])


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
    