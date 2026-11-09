"""Vercel Serverless Function entrypoint for FastAPI backend."""

import sys
import types
from pathlib import Path

# Ensure project root is in sys.path so 'backend' is importable
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"

for path in (str(ROOT_DIR), str(BACKEND_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

if "backend" not in sys.modules and BACKEND_DIR.exists():
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [str(BACKEND_DIR)]
    sys.modules["backend"] = backend_pkg

from backend.app.main import app
from backend.app.models.database import init_db

# Ensure database tables exist in serverless environment safely without crashing cold start
try:
    init_db()
except Exception as e:
    print(f"Database auto-init on serverless cold start: {e}")

# 'app' is the FastAPI instance that Vercel's Python runtime will serve
