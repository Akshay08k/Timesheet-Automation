"""Authentication API routes using MongoDB."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pymongo.database import Database
from backend.app.config.settings import get_settings
from backend.app.models.database import get_db, get_next_sequence_value
from backend.app.models.user import User
from backend.app.schemas.auth import UserCreate, UserResponse, Token
from backend.app.security.jwt import hash_password, verify_password, create_access_token
from backend.app.api.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _validate_allowed_email_domain(email: str):
    """Enforces email domain restriction for security if configured."""
    allowed = (settings.allowed_email_domain or "").lower().strip()
    if allowed and allowed != "*":
        domain = allowed if allowed.startswith("@") else f"@{allowed}"
        if not email.lower().endswith(domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Access restricted. Only '{domain}' email addresses are permitted.",
            )


@router.post("/register", response_model=UserResponse)
def register_user(user_in: UserCreate, db: Database = Depends(get_db)):
    """Registers a new user in MongoDB. The first registered user automatically becomes an admin."""
    # Enforce email domain restriction
    _validate_allowed_email_domain(user_in.email)

    username = user_in.username or user_in.email.split("@")[0].strip()

    # Check if username or email already exists
    existing = db.users.find_one(
        {"$or": [{"username": username}, {"email": user_in.email}]}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered.")

    # Check if this is the first user
    user_count = db.users.count_documents({})
    is_first_user = (user_count == 0)

    user_id = get_next_sequence_value(db, "users")

    user = User(
        id=user_id,
        username=username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        is_admin=True if is_first_user else user_in.is_admin,
        timezone=user_in.timezone,
    )

    db.users.insert_one(user.to_dict())
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Database = Depends(get_db)):
    """Authenticates user against MongoDB and returns JWT token."""
    user_doc = db.users.find_one(
        {"$or": [{"username": form_data.username}, {"email": form_data.username}]}
    )

    if not user_doc or not verify_password(form_data.password, user_doc.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Domain security check on login
    allowed = (settings.allowed_email_domain or "").lower().strip()
    if allowed and allowed != "*":
        domain = allowed if allowed.startswith("@") else f"@{allowed}"
        user_email = (user_doc.get("email") or "").lower()
        if not user_email.endswith(domain):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted: Only '{domain}' accounts are permitted to sign in.",
            )

    user = User.from_doc(user_doc)
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
