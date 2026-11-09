"""Entrypoint for Vercel FastAPI backend."""

import sys
import types
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent

# Ensure 'backend' package resolves cleanly in all deployment environments
if "backend" not in sys.modules:
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [str(BACKEND_DIR)]
    sys.modules["backend"] = backend_pkg

for path in (str(ROOT_DIR), str(BACKEND_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.app.main import app  # noqa: E402, F401
