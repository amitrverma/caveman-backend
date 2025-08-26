from pywebpush import webpush, WebPushException
from app.config import settings

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

        if status_code == 410:
            # handle deletion of subscription from database
        elif status_code == 404:
            # handle subscription not found
        elif status_code == 400:
            # handle malformed request
        elif status_code == 401:
            # handle authentication issues
        return None

