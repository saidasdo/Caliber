"""Vercel entrypoint: exposes the FastAPI app from backend/app/main.py as an ASGI
function. vercel.json rewrites /api/* here; the FastAPI routers (already mounted
with prefix="/api") handle the rest of the routing from the original request path.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402
