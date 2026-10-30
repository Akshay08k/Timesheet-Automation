"""FastAPI dependencies for authentication and authorization."""

from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.models.database import get_db
from backend.app.models.user import User
from backend.app.security.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validates JWT and returns the current authenticated user, ensuring strict multi-user isolation."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.scalars(select(User).where(User.id == int(user_id))).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or deleted.")

    return user
