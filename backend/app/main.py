"""FastAPI Application entrypoint for DevTimesheet."""

import sys
from pathlib import Path

# Ensure root directory (containing 'backend') is in sys.path
_current_dir = Path(__file__).resolve().parent
_backend_dir = _current_dir.parent
_root_dir = _backend_dir.parent
for _p in (str(_root_dir), str(_backend_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config.settings import get_settings
from backend.app.models.database import init_db, close_db, check_database_health
from backend.app.api.auth_routes import router as auth_router
from backend.app.api.credential_routes import router as credential_router
from backend.app.api.activity_routes import router as activity_router
from backend.app.api.manual_activity_routes import router as manual_activity_router
from backend.app.api.summary_routes import router as summary_router
from backend.app.api.timesheet_routes import router as timesheet_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MongoDB collections and indexes
    init_db()
    yield
    # Close connection pool on shutdown
    close_db()


settings = get_settings()

app = FastAPI(
    title="DevTimesheet API",
    description="Local-hosted multi-user timesheet automation with MongoDB, Azure DevOps & Google Gemini API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware for local frontend & Vercel deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth_router)
app.include_router(credential_router)
app.include_router(activity_router)
app.include_router(manual_activity_router)
app.include_router(summary_router)
app.include_router(timesheet_router)


@app.get("/")
def root():
    db_status = check_database_health()
    return {
        "app": "DevTimesheet API",
        "status": "running",
        "database": "MongoDB Atlas" if not db_status.get("is_mock") else "In-Memory Mock",
        "database_connected": db_status.get("connected", False),
        "docs_url": "/docs",
        "health_url": "/api/health",
    }


@app.get("/api/health")
def health_check():
    db_status = check_database_health()
    return {
        "status": "healthy" if db_status.get("connected") else "degraded",
        "app": "DevTimesheet",
        "database": "MongoDB",
        "database_connected": db_status.get("connected", False),
        "is_mock_database": db_status.get("is_mock", False),
        "database_details": db_status,
        "version": "1.0.0",
        "gemini_model": settings.gemini_model,
    }
