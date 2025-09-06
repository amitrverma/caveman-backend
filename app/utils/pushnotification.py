from pywebpush import webpush, WebPushException
from app.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from app.models import WebPushSubscription
import logging
import json

logger = logging.getLogger(__name__)

async def send_push(subscription: dict, payload: str, db: AsyncSession, sub_id=None):
    """
    subscription: dict with {endpoint, keys}
    payload: str (JSON payload to send)
    db: AsyncSession (so we can delete expired subs)
    sub_id: optional UUID of the subscription row (to delete if expired)
    """
    try:
        response = webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"}
        )
        return response

    except WebPushException as ex:
        status_code = getattr(ex.response, "status_code", None)
        logger.error(f"WebPushException: {ex} (status {status_code})")

        # ❌ Remove expired/invalid subscriptions from DB
        if status_code in (404, 410):  # not found / gone
            if sub_id:
                logger.warning(f"Deleting expired subscription {sub_id}")
                await db.execute(delete(WebPushSubscription).where(WebPushSubscription.id == sub_id))
                await db.commit()

        elif status_code == 400:
            logger.warning("Push request malformed (400).")
        elif status_code == 401:
            logger.error("Push authentication failed (401).")
        else:
            logger.error("Unhandled WebPush error.")

        return None
