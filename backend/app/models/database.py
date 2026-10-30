"""Database engine and session management."""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config.settings import get_settings
from backend.app.models.base import Base

settings = get_settings()

db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Handle Vercel serverless environment for SQLite
if os.environ.get("VERCEL") and db_url.startswith("sqlite") and "data" in db_url:
    db_url = "sqlite:////tmp/devtimesheet.db"

# Ensure parent directory for SQLite database exists
if db_url.startswith("sqlite"):
    # Strip sqlite prefix to extract filesystem path
    clean_path = db_url.replace("sqlite:////", "/").replace("sqlite:///", "")
    dir_name = os.path.dirname(os.path.abspath(clean_path))
    if dir_name:
        try:
            Path(dir_name).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
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
