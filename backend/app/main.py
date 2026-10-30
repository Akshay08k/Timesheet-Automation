"""FastAPI Application entrypoint for DevTimesheet."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config.settings import get_settings
from backend.app.models.database import init_db
from backend.app.api.auth_routes import router as auth_router
from backend.app.api.credential_routes import router as credential_router
from backend.app.api.activity_routes import router as activity_router
from backend.app.api.manual_activity_routes import router as manual_activity_router
from backend.app.api.summary_routes import router as summary_router
from backend.app.api.timesheet_routes import router as timesheet_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    init_db()
    yield


settings = get_settings()

app = FastAPI(
    title="DevTimesheet API",
    description="Local-hosted multi-user timesheet automation with Azure DevOps & Google Gemini API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": "DevTimesheet",
        "version": "1.0.0",
        "gemini_model": settings.gemini_model,
    }
