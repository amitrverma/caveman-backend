from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import WebPushSubscription
from app.database import get_db
from app.utils.pushnotification import send_push
from app.utils.reminder_engine import send_spot_pushes, send_microchallenge_pushes
import json
from app.utils.reminder_engine import send_daily_nudge

router = APIRouter()

from sqlalchemy import select
from app.models import User

@router.post("/send-daily-nudge")
async def send_daily_nudge(db: AsyncSession = Depends(get_db)):
    result = await send_daily_nudge(db)
    return {"status": "ok", **result}

@router.post("/push-spot")
async def trigger_spot_pushes(db: AsyncSession = Depends(get_db)):
    await send_spot_pushes(db)
    return {"status": "spot nudges sent"}

@router.post("/push-challenge")
async def trigger_challenge_pushes(db: AsyncSession = Depends(get_db)):
    await send_microchallenge_pushes(db)
    return {"status": "microchallenge nudges sent"}