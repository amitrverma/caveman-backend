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
        print(f"🔥 Web push failed for {subscription['endpoint']}: {ex}")
        return None
