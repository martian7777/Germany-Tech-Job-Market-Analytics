"""Vercel serverless entry point for the DeTech Jobs Analytics backend.

Vercel's @vercel/python runtime imports the ASGI ``app`` exposed here. All
``/api/*`` traffic is rewritten to this function (see ../vercel.json); FastAPI
receives the original request path, which already matches its ``/api/...``
route prefixes, so no path rewriting is needed inside the app.
"""

from __future__ import annotations

import os
import sys

# Make the backend package (``app``) importable from the repo's backend/ dir.
_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, _BACKEND_DIR)

# On Vercel the only writable location is /tmp; point SQLite there. Locally this
# env var is normally unset, so the default path in database.py is used instead.
os.environ.setdefault("DETECH_DATABASE_URL", "sqlite:////tmp/detech_jobs.db")

from app.main import app  # noqa: E402  (import after sys.path / env setup)
from app.seed import seed  # noqa: E402

# Vercel's ASGI adapter does not always fire FastAPI's lifespan startup hook, so
# create the schema and seed the demo dataset here at cold start. Idempotent:
# keep_existing skips reseeding when the (warm) /tmp database already has data.
seed(keep_existing=True)

# Expose ``app`` for the runtime.
__all__ = ["app"]
