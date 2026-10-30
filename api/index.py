"""Vercel Serverless Function entrypoint for FastAPI backend."""

import sys
from pathlib import Path

# Ensure project root is in sys.path so 'backend' is importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.models.database import init_db

# Ensure database tables exist in serverless environment
try:
    init_db()
except Exception as e:
    print(f"Database auto-init on serverless cold start: {e}")

# 'app' is the FastAPI instance that Vercel's Python runtime will serve
