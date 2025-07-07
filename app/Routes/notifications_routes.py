from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import WebPushSubscription
from app.database import get_db
from app.utils.pushnotification import send_push
from app.utils.reminder_engine import send_spot_pushes, send_microchallenge_pushes
import json
from app.helper.common import get_random_active_nudge
from app.Routes.whatsapp_routes import send_whatsapp_message

router = APIRouter()

from sqlalchemy import select
from app.models import User

@router.post("/send-daily-nudge")
async def send_daily_nudge(db: AsyncSession = Depends(get_db)):
    nudge = await get_random_active_nudge(db)

    # Format for push notifications
    payload = {
        "title": nudge.title or "🧠 Caveman Nudge",
        "body": nudge.quote or (nudge.paragraphs[0] if nudge.paragraphs else "Here's your daily nudge.")
    }

    # Format WhatsApp message
    message = (
        f"*{nudge.title or '💡 Nudge of the Day'}*\n\n"
        + "\n\n".join(nudge.paragraphs or [])
    )
    if nudge.quote:
        message += f"\n\n_{nudge.quote}_"

    # Send WebPush notifications
    result = await db.execute(select(WebPushSubscription))
    subs = result.scalars().all()

    push_success = 0
    for sub in subs:
        sub_info = {
            "endpoint": sub.endpoint,
            "keys": sub.keys
        }
        result = send_push(sub_info, payload=json.dumps(payload))
        if result:
            push_success += 1

    # Fetch opted-in users for WhatsApp
    result = await db.execute(
        select(User).where(User.whatsapp_opt_in == True)
    )
    whatsapp_users = result.scalars().all()

    whatsapp_success = 0
    for user in whatsapp_users:
        if user.phone_number:  # Make sure number exists
            sent = send_whatsapp_message(user.phone_number, message)
            if sent:
                whatsapp_success += 1

    return {
        "message": f"Sent {push_success} pushes and {whatsapp_success} WhatsApp messages",
        "nudge_id": str(nudge.id),
        "preview": payload,
        "whatsapp_message": message
    }




@router.post("/push-spot")
async def trigger_spot_pushes(db: AsyncSession = Depends(get_db)):
    await send_spot_pushes(db)
    return {"status": "spot nudges sent"}

@router.post("/push-challenge")
async def trigger_challenge_pushes(db: AsyncSession = Depends(get_db)):
    await send_microchallenge_pushes(db)
    return {"status": "microchallenge nudges sent"}