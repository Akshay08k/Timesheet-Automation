"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.models.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import UserCreate, UserResponse, Token
from backend.app.security.jwt import hash_password, verify_password, create_access_token
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Registers a new user. The first registered user automatically becomes an admin."""
    # Check if username or email already exists
    existing_user = db.scalars(
        select(User).where((User.username == user_in.username) | (User.email == user_in.email))
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered.")

    # Check if this is the first user
    user_count = len(db.scalars(select(User.id)).all())
    is_first_user = (user_count == 0)

    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        is_admin=True if is_first_user else user_in.is_admin,
        timezone=user_in.timezone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticates user and returns JWT token."""
    user = db.scalars(
        select(User).where((User.username == form_data.username) | (User.email == form_data.username))
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id), "username": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns profile for currently authenticated user."""
    return current_user
