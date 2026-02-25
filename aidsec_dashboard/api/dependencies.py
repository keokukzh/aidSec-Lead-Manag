"""FastAPI dependencies: database sessions and authentication."""
import os
from typing import Generator, Optional
from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from database.database import SessionLocal

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_token = HTTPBearer(auto_error=False)

# Rate limiter instance (shared with main.py)
limiter = Limiter(key_func=get_remote_address)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_api_key(
    api_key: str = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_token)
) -> str:
    """Validate the API key or Bearer token from the request header.
    If no API_KEY is configured in .env, all requests are allowed."""
    expected = os.getenv("API_KEY", "")

    # If no API key required, allow all requests
    if not expected:
        return ""

    # Check API key
    if api_key and api_key == expected:
        return api_key

    # Check Bearer token
    if bearer and bearer.credentials:
        allowed_bearers = {
            "authenticated-token",  # issued by /auth/login in current simple auth flow
            expected,
        }
        if bearer.credentials in allowed_bearers:
            return bearer.credentials

    raise HTTPException(status_code=401, detail="Invalid or missing API key")


def get_limiter():
    """Get the rate limiter instance."""
    return limiter


def rate_limit(default_limit: str = "30/minute"):
    """Dependency that applies rate limiting to endpoints."""
    from fastapi import Request
    def rate_limiter(request: Request):
        return limiter.limit(default_limit)(request)
    return rate_limiter
