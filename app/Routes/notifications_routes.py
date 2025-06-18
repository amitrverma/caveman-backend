from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import WebPushSubscription
from app.database import get_db
from app.utils.pushnotification import send_push
from app.utils.reminder_engine import send_spot_pushes, send_microchallenge_pushes
import json

router = APIRouter()

@router.post("/send-daily-nudge")
async def send_daily_nudge(db: AsyncSession = Depends(get_db)):
    stmt = select(WebPushSubscription)
    result = await db.execute(stmt)
    subs = result.scalars().all()

    payload = {
        "title": "🧠 Daily Caveman Nudge",
        "body": "Mismatch of the day: your brain still treats status like survival. Choose your focus wisely."
    }

    success = 0
    for sub in subs:
        sub_info = {
            "endpoint": sub.endpoint,
            "keys": sub.keys
        }
        result = send_push(sub_info, payload=json.dumps(payload))
        if result:
            success += 1

    return {"message": f"Sent {success} pushes"}


@router.post("/push-spot")
async def trigger_spot_pushes(db: AsyncSession = Depends(get_db)):
    await send_spot_pushes(db)
    return {"status": "spot nudges sent"}

@router.post("/push-challenge")
async def trigger_challenge_pushes(db: AsyncSession = Depends(get_db)):
    await send_microchallenge_pushes(db)
    return {"status": "microchallenge nudges sent"}