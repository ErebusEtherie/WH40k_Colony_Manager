"""CSRF protection middleware.

This middleware validates CSRF tokens on state-changing requests to prevent
Cross-Site Request Forgery attacks.
"""

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Validate CSRF tokens on state-changing requests.

    This middleware:
    - Skips CSRF validation for safe methods (GET, HEAD, OPTIONS)
    - Requires X-CSRF-Token header for POST, PUT, PATCH, DELETE
    - Validates token matches the cookie value
    - Exempts only the pre-authentication auth endpoints that run before a
      session exists (login/register have rate limiting instead; refresh and
      csrf-token are not state-changing in the CSRF sense / run pre-auth).
      Authenticated state-changers under ``/auth`` (change-password, revoke,
      revoke-all) are NOT exempt and MUST carry a valid CSRF token.
    """

    # Auth endpoints that legitimately run without an established session and
    # therefore cannot present a CSRF token. Everything else under /api/v1/auth
    # (change-password, revoke, revoke-all) is an authenticated state-changing
    # request and must be CSRF-protected like any other mutating request.
    EXEMPT_AUTH_PATHS = frozenset(
        {
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/csrf-token",
        }
    )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip CSRF check for safe methods
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        # Skip CSRF only for the pre-auth auth endpoints listed above.
        if request.url.path in self.EXEMPT_AUTH_PATHS:
            return await call_next(request)

        # Get CSRF token from header
        csrf_token = request.headers.get("X-CSRF-Token")

        if not csrf_token:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "CSRF token missing. Please refresh the page.",
                    "path": request.url.path,
                },
            )

        # Validate CSRF token against cookie
        cookie_token = request.cookies.get("csrf_token")

        if not cookie_token or csrf_token != cookie_token:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "CSRF token invalid. Please refresh the page.",
                    "path": request.url.path,
                },
            )

        return await call_next(request)
