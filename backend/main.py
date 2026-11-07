"""Entrypoint for Vercel FastAPI service when root is set to 'backend'."""

import sys
from pathlib import Path

# Ensure root directory (containing 'backend') and backend directory are in sys.path
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent

for path in (str(ROOT_DIR), str(BACKEND_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.app.main import app  # noqa: E402, F401

