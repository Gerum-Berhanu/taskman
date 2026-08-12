from typing import Annotated, Any
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
from starlette.status import HTTP_401_UNAUTHORIZED

from app.config import settings
from app.storage import UserStore, user_store


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_user_store() -> UserStore:
    return user_store


UserStoreDep = Annotated[UserStore, Depends(get_user_store)]


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], storage: UserStoreDep):
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception

    user = storage.get_by_email(email)
    if user is None:
        raise credentials_exception
    return user


CurrentUserDep = Annotated[dict[str, Any], Depends(get_current_user)]