"""Authentication routes for the AidSec API."""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """Authenticate user and return access token."""
    app_password = os.getenv("APP_PASSWORD", "")

    # If no password is set, allow any login
    if not app_password:
        return LoginResponse(
            access_token="dummy-token-when-no-password",
            token_type="bearer"
        )

    # Check password
    if request.password == app_password:
        return LoginResponse(
            access_token="authenticated-token",
            token_type="bearer"
        )

    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/logout")
def logout():
    """Logout endpoint (no-op for simple auth)."""
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_current_user():
    """Get current user info."""
    return {"user": "admin"}
