"""Pydantic models for user endpoints."""

from pydantic import BaseModel, Field


class TelegramStatusResponse(BaseModel):
    """Response model for Telegram link status."""

    is_linked: bool = Field(..., description="Whether Telegram is linked")
    chat_id: str | None = Field(None, description="Linked chat ID (masked)")


class TelegramLinkCodeResponse(BaseModel):
    """Response model for generating a link code."""

    code: str = Field(..., description="One-time link code")
    expires_in_seconds: int = Field(..., description="Seconds until code expires")
    instructions: str = Field(..., description="Instructions for the user")


class TelegramUnlinkResponse(BaseModel):
    """Response model for unlinking Telegram."""

    ok: bool = Field(..., description="Whether unlink was successful")
