"""Database engine and session management."""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config.settings import get_settings
from backend.app.models.base import Base

settings = get_settings()

# Ensure parent directory for SQLite database exists
if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.replace("sqlite:///", "")
    Path(os.path.dirname(os.path.abspath(db_path))).mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initializes database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency yielding database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
