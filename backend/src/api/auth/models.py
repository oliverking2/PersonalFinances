"""Pydantic models for authentication endpoints."""

from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request model for login endpoint."""

    username: str = Field(..., min_length=1, description="User's username")
    password: str = Field(..., min_length=1, description="User's password")


class RegisterRequest(BaseModel):
    """Request model for register endpoint."""

    username: str = Field(..., min_length=3, max_length=50, description="User's username")
    password: str = Field(..., min_length=8, description="User's password")


class TokenResponse(BaseModel):
    """Response model for token endpoints (login, refresh)."""

    access_token: str = Field(..., description="JWT access token")
    expires_in: int = Field(..., description="Token expiry in seconds")


class LogoutResponse(BaseModel):
    """Response model for logout endpoint."""

    ok: bool = Field(..., description="Whether logout was successful")


class UserResponse(BaseModel):
    """Response model for user information."""

    id: UUID = Field(..., description="User's unique identifier")
    username: str = Field(..., description="User's username")

    model_config = {"from_attributes": True}
