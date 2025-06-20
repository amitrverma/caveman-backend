from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import WebPushSubscription
from app.database import get_db
from app.utils.pushnotification import send_push
from app.utils.reminder_engine import send_spot_pushes, send_microchallenge_pushes
import json
from app.helper.common import get_random_active_nudge

router = APIRouter()

@router.post("/send-daily-nudge")
async def send_daily_nudge(db: AsyncSession = Depends(get_db)):
    nudge = await get_random_active_nudge(db)

    payload = {
        "title": nudge.title or "🧠 Caveman Nudge",
        "body": nudge.quote or nudge.paragraphs[0]  # fallback
    }

    result = await db.execute(select(WebPushSubscription))
    subs = result.scalars().all()

    success = 0
    for sub in subs:
        sub_info = {
            "endpoint": sub.endpoint,
            "keys": sub.keys
        }
        result = send_push(sub_info, payload=json.dumps(payload))
        if result:
            success += 1

    return {
        "message": f"Sent {success} pushes",
        "nudge_id": str(nudge.id),
        "preview": payload
    }



@router.post("/push-spot")
async def trigger_spot_pushes(db: AsyncSession = Depends(get_db)):
    await send_spot_pushes(db)
    return {"status": "spot nudges sent"}

@router.post("/push-challenge")
async def trigger_challenge_pushes(db: AsyncSession = Depends(get_db)):
    await send_microchallenge_pushes(db)
    return {"status": "microchallenge nudges sent"}