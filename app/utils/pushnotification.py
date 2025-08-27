from pywebpush import webpush, WebPushException
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def send_push(subscription: dict, payload: str):
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

        if status_code == 410:
            # Subscription is gone (e.g. user unsubscribed) → delete from DB
            logger.warning("Push subscription expired (410). Should delete from DB.")
        elif status_code == 404:
            # Subscription not found
            logger.warning("Push subscription not found (404).")
        elif status_code == 400:
            # Malformed request
            logger.warning("Push request malformed (400).")
        elif status_code == 401:
            # Authentication issues (wrong keys, etc.)
            logger.error("Push authentication failed (401).")
        else:
            logger.error("Unhandled WebPush error.")

        return None
