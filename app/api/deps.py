"""Shared FastAPI dependencies: DB session and the current user."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User
from app.services import users as user_service

AUTH_COOKIE = "access_token"

# auto_error=False: we also accept the token from the web UI's HttpOnly cookie.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user_optional(
    request: Request,
    db: DbSession,
    bearer: Annotated[str | None, Depends(oauth2_scheme)],
) -> User | None:
    """The signed-in user (Bearer header for the API, cookie for the web UI), or None."""
    token = bearer or request.cookies.get(AUTH_COOKIE)
    if not token:
        return None
    username = decode_access_token(token)
    if username is None:
        return None
    user = user_service.get_by_username(db, username)
    return user if user and user.is_active else None


def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
CurrentUser = Annotated[User, Depends(get_current_user)]
