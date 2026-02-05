"""
Dependency injection for BrasilIntel API.

Provides reusable dependencies for FastAPI routes.
"""
import secrets
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal

# HTTP Basic authentication scheme for admin interface
security = HTTPBasic()


def verify_admin(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)]
) -> str:
    """
    Verify HTTP Basic credentials for admin access.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        credentials: HTTP Basic credentials from request
        settings: Application settings with admin username/password

    Returns:
        Username on successful authentication

    Raises:
        HTTPException 401: If credentials are invalid or password not configured
    """
    # Require password to be configured (not empty)
    if not settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin password not configured. Set ADMIN_PASSWORD env var.",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Use constant-time comparison to prevent timing attacks
    username_correct = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.admin_username.encode("utf-8")
    )
    password_correct = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.admin_password.encode("utf-8")
    )

    if not (username_correct and password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Yields a SQLAlchemy session and ensures cleanup after request completion.
    Note: Commit happens in endpoint handlers, not here, to support
    proper transaction control per FastAPI best practices.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
