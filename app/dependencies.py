"""
Dependency injection for BrasilIntel API.

Provides reusable dependencies for FastAPI routes.
"""
from collections.abc import Generator
from sqlalchemy.orm import Session
from app.database import SessionLocal


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
