"""User API endpoints for profile and settings management."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.api.responses import RESOURCE_RESPONSES
from src.api.user.models import (
    TelegramLinkCodeResponse,
    TelegramStatusResponse,
    TelegramUnlinkResponse,
)
from src.postgres.auth.models import User
from src.postgres.auth.operations.users import unlink_telegram
from src.postgres.telegram import create_link_code

logger = logging.getLogger(__name__)

router = APIRouter()


# Minimum chat ID length to show partial characters
_MIN_MASK_LENGTH = 4


def _mask_chat_id(chat_id: str) -> str:
    """Mask a chat ID for display, showing only first 2 and last 2 chars.

    :param chat_id: The chat ID to mask.
    :returns: Masked chat ID string.
    """
    if len(chat_id) <= _MIN_MASK_LENGTH:
        return "*" * len(chat_id)
    return f"{chat_id[:2]}{'*' * (len(chat_id) - _MIN_MASK_LENGTH)}{chat_id[-2:]}"


@router.get(
    "/telegram",
    response_model=TelegramStatusResponse,
    summary="Get Telegram link status",
    responses=RESOURCE_RESPONSES,
)
def get_telegram_status(
    current_user: User = Depends(get_current_user),
) -> TelegramStatusResponse:
    """Check if the user's account is linked to Telegram."""
    is_linked = current_user.telegram_chat_id is not None
    masked_chat_id = (
        _mask_chat_id(current_user.telegram_chat_id) if current_user.telegram_chat_id else None
    )

    return TelegramStatusResponse(
        is_linked=is_linked,
        chat_id=masked_chat_id,
    )


@router.post(
    "/telegram/link",
    response_model=TelegramLinkCodeResponse,
    summary="Generate Telegram link code",
    responses=RESOURCE_RESPONSES,
)
def generate_telegram_link_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramLinkCodeResponse:
    """Generate a one-time code for linking Telegram account.

    The user should send this code to the Telegram bot to complete the linking.
    Codes expire after 10 minutes.
    """
    if current_user.telegram_chat_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Telegram is already linked. Unlink first to relink.",
        )

    link_code = create_link_code(db, current_user.id)
    db.commit()

    expires_in = int((link_code.expires_at - datetime.now(UTC)).total_seconds())

    logger.info(f"Generated Telegram link code: user_id={current_user.id}")

    return TelegramLinkCodeResponse(
        code=link_code.code,
        expires_in_seconds=expires_in,
        instructions="Send /link {code} to the bot to complete linking.",
    )


@router.delete(
    "/telegram",
    response_model=TelegramUnlinkResponse,
    summary="Unlink Telegram account",
    responses=RESOURCE_RESPONSES,
)
def unlink_telegram_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramUnlinkResponse:
    """Unlink the Telegram account from the user's profile."""
    if current_user.telegram_chat_id is None:
        raise HTTPException(
            status_code=400,
            detail="Telegram is not linked.",
        )

    unlink_telegram(db, current_user.id)
    db.commit()

    logger.info(f"Unlinked Telegram: user_id={current_user.id}")

    return TelegramUnlinkResponse(ok=True)
