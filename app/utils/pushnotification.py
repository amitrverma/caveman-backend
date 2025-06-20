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
        print(f"✅ Push sent: {subscription['endpoint']}, Status: {response.status_code}")
        return response
    except WebPushException as ex:
        status_code = getattr(ex.response, "status_code", None)
        print(f"🔥 Web push failed: {subscription['endpoint']} | Status: {status_code} | Error: {str(ex)}")

        if status_code == 410:
            print("💀 Subscription is gone — delete from DB.")
        elif status_code == 404:
            print("❌ Subscription not found.")
        elif status_code == 400:
            print("⚠️ Malformed subscription or payload.")
        elif status_code == 401:
            print("🔐 Auth/VAPID key issue.")
        return None

