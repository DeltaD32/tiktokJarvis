"""Auth middleware — extracts JWT from Authorization header, attaches user to request.

Only active when DELA_MULTI_USER env var is set to "1".

Skips auth for:
  - /health, /docs, /openapi.json, /redoc
  - /api/auth/login, /api/auth/refresh (public endpoints)
  - Non-/api/* paths (static files, WebSocket negotiation)

On valid token, injects request.state.user = {id, username, role}.
On missing/invalid/expired token, returns 401 JSON.
"""

from __future__ import annotations

import os

import jwt as pyjwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

SKIP_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/auth/login",
    "/api/auth/refresh",
}


def _is_multi_user() -> bool:
    return os.getenv("DELA_MULTI_USER", "0") == "1"


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Always attach an empty user (backward compat when multi-user is off)
        request.state.user = None

        if not _is_multi_user():
            return await call_next(request)

        path = request.url.path

        # Skip auth for public paths and non-API routes
        if path in SKIP_PATHS or not path.startswith("/api/"):
            return await call_next(request)

        from dela import auth, users

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization header"})

        token = auth_header[len("Bearer "):]

        try:
            payload = auth.decode_token(token)
        except pyjwt.PyJWTError:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        if users.is_session_revoked(payload.get("jti", "")):
            return JSONResponse(status_code=401, content={"detail": "Token has been revoked"})

        request.state.user = {
            "id": payload["sub"],
            "username": payload["username"],
            "role": payload["role"],
        }

        # Set thread-local user context so state modules resolve per-user paths
        from dela import user_context as _uc
        _uc.set_current_user_id(payload["sub"])

        try:
            response = await call_next(request)
        finally:
            _uc.clear_current_user_id()
        return response


def require_admin(request: Request) -> bool:
    """Return True if the authenticated user is an admin."""
    user = getattr(request.state, "user", None)
    return user is not None and user.get("role") == "admin"


def require_user(request: Request) -> bool:
    """Return True if the request has an authenticated user (any role)."""
    return getattr(request.state, "user", None) is not None


def get_current_user(request: Request) -> dict | None:
    """Return the current user dict from request state, or None."""
    return getattr(request.state, "user", None)
