import json
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CavemanSpot, MicrochallengeLog, WebPushSubscription
from app.utils.pushnotification import send_push
from app.models import User
from app.Routes.whatsapp_routes import send_whatsapp_message
from app.helper.common import get_random_active_nudge

async def has_spotted_today(user_id, db: AsyncSession):
    stmt = select(CavemanSpot).where(
        CavemanSpot.user_id == user_id,
        CavemanSpot.date == date.today()
    )
    result = await db.execute(stmt)
    return result.scalars().first() is not None


async def has_logged_micro_today(user_id, db: AsyncSession):
    stmt = select(MicrochallengeLog).where(
        MicrochallengeLog.user_id == user_id,
        MicrochallengeLog.log_date == date.today()
    )
    result = await db.execute(stmt)
    return result.scalars().first() is not None


async def send_spot_pushes(db: AsyncSession):
    stmt = select(WebPushSubscription.user_id).distinct()
    users_result = await db.execute(stmt)
    user_ids = users_result.scalars().all()

    for user_id in user_ids:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            continue

        devices_stmt = select(WebPushSubscription).where(WebPushSubscription.user_id == user_id)
        devices_result = await db.execute(devices_stmt)
        subscriptions = devices_result.scalars().all()

        if await has_spotted_today(user_id, db):
            title = "🧠 Awareness Activated"
            body = "Nice job spotting your caveman today!"
        else:
            title = "👀 Caveman Check-in"
            body = "Did you notice your instincts in action today?"

        # Web push
        for sub in subscriptions:
            send_push(
                {"endpoint": sub.endpoint, "keys": sub.keys},
                payload=json.dumps({"title": title, "body": body})
            )

        # WhatsApp message
        if user.phone_number and getattr(user, "whatsapp_opt_in", True):  # Add opt-in check if applicable
            send_whatsapp_message(user.phone_number, f"{title} {body}")



async def send_microchallenge_pushes(db: AsyncSession):
    stmt = select(WebPushSubscription.user_id).distinct()
    users_result = await db.execute(stmt)
    user_ids = users_result.scalars().all()

    for user_id in user_ids:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            continue

        devices_stmt = select(WebPushSubscription).where(WebPushSubscription.user_id == user_id)
        devices_result = await db.execute(devices_stmt)
        subscriptions = devices_result.scalars().all()

        if await has_logged_micro_today(user_id, db):
            title = "🔥 Consistency Hit"
            body = "You showed up again. That’s what builds momentum."
        else:
            title = "💡 Today's Micro Win"
            body = "Your daily challenge is still open. Quick check-in?"

        # Web push
        for sub in subscriptions:
            send_push(
                {"endpoint": sub.endpoint, "keys": sub.keys},
                payload=json.dumps({"title": title, "body": body})
            )

        # WhatsApp
        if user.phone_number and getattr(user, "whatsapp_opt_in", True):
            send_whatsapp_message(user.phone_number, f"{title} {body}")

async def send_daily_nudge(db: AsyncSession):
    nudge = await get_random_active_nudge(db)

    payload = {
        "title": nudge.title or "🧠 Caveman Nudge",
        "body": nudge.quote or (nudge.paragraphs[0] if nudge.paragraphs else "Here's your daily nudge.")
    }

    message = (
        f"*{nudge.title or '💡 Nudge of the Day'}*\n\n"
        + "\n\n".join(nudge.paragraphs or [])
    )
    if nudge.quote:
        message += f"\n\n_{nudge.quote}_"

    # Web Push
    result = await db.execute(select(WebPushSubscription))
    subs = result.scalars().all()

    push_success = 0
    for sub in subs:
        sub_info = {"endpoint": sub.endpoint, "keys": sub.keys}
        if send_push(sub_info, payload=json.dumps(payload)):
            push_success += 1

    # WhatsApp
    result = await db.execute(select(User).where(User.whatsapp_opt_in == True))
    whatsapp_users = result.scalars().all()

    whatsapp_success = 0
    for user in whatsapp_users:
        if user.phone_number:
            if send_whatsapp_message(user.phone_number, message):
                whatsapp_success += 1

    return {
        "nudge_id": str(nudge.id),
        "push_success": push_success,
        "whatsapp_success": whatsapp_success,
        "preview": payload,
        "whatsapp_message": message,
    }