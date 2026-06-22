"""
FastAPI dependencies for the IUNA API.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer_scheme = HTTPBearer(auto_error=False)


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str | None:
    """
    Validate the Bearer token against the configured API_SECRET_TOKEN.

    - If API_SECRET_TOKEN is not configured (None/empty) → skip validation (dev mode).
    - If token doesn't match → raise HTTP 401.

    Returns the token string if valid, or None in dev mode.
    """
    # Dev mode: no token configured, skip validation
    if not settings.API_SECRET_TOKEN:
        return None

    # Token is required but not provided
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Token provided but doesn't match
    if credentials.credentials != settings.API_SECRET_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
