# src/api/routes/webhook.py
import hmac
from hashlib import sha256
from fastapi import APIRouter, Header, HTTPException, Body, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.database import get_sqlite_db
from src.logging_config import app_logger
from src.schema.video import HeyGenWebhookEvent
from src.services.dialogue.video import heygen_event_handler
from src.settings import settings


router = APIRouter(prefix="/webhooks")


@router.post("/heygen", status_code=200)
async def heygen_webhook(
    event: HeyGenWebhookEvent = Body(...),
    signature: str = Header(None, alias="Signature"),
    db: Session = Depends(get_sqlite_db)
):
    """
    Endpoint to receive webhook events from HeyGen
    Uses Pydantic model for automatic validation
    Verifies the signature via header
    Returns simple HTTP 200 response
    """
    app_logger.info(f"Received HeyGen webhook event: {event}")
    app_logger.info(f"Signature: {signature}")
    # Verify signature if provided and configured
    if signature and settings.HEYGEN_WEBHOOK_SECRET:
        # Use model_dump_json to get the JSON string directly
        # Set exclude_none=False and by_alias=False to match HeyGen's signing method
        # Use compact JSON with no indentation and separators to minimize whitespace
        body_str = event.model_dump_json(
            exclude_none=False,
            by_alias=False,
            indent=None
        )

        computed_sig = hmac.new(
            settings.HEYGEN_WEBHOOK_SECRET.encode("utf-8"),
            msg=body_str.encode("utf-8"),
            digestmod=sha256
        ).hexdigest()

        if computed_sig != signature:
            raise HTTPException(status_code=401, detail="Invalid signature")

    return (
        Response(status_code=200)
        if await heygen_event_handler(event, db)
        else Response(status_code=500)
    )
