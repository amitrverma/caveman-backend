from fastapi import APIRouter, Depends, Header, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from app.database import get_db
from app.models import CavemanSpot, MicrochallengeDefinition, MicrochallengeLog
from app.schemas import SpotCreate, SpotResponse
from datetime import datetime, date
import uuid
import jwt
from app.config import settings
from typing import Optional

router = APIRouter()

FAKE_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")  # TODO: Replace with real user from JWT

def get_current_user(authorization: str = Header(...)):
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid auth scheme")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return uuid.UUID(payload["sub"])  # returning UUID not string now
    except Exception as e:
        print("JWT decode error:", e)
        raise HTTPException(status_code=401, detail="Invalid or missing token")

### ✅ CavemanSpot routes remain unchanged ###

@router.post("/spots", response_model=SpotResponse)
async def create_spot(
    spot: SpotCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user)
):
    try:
        new_spot = CavemanSpot(
            user_id=user_id,
            description=spot.description,
            date=spot.date or date.today(),
            created_at=datetime.utcnow(),
        )
        db.add(new_spot)
        await db.commit()
        await db.refresh(new_spot)
        return new_spot
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create spot: {str(e)}")

@router.get("/spots", response_model=list[SpotResponse])
async def get_spots(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user)
):
    result = await db.execute(
        select(CavemanSpot).where(CavemanSpot.user_id == user_id).order_by(CavemanSpot.date.desc())
    )
    return result.scalars().all()

### 🔥 ✅ Microchallenge routes start here ✅ 🔥

@router.get("/microchallenge/active")
async def get_active_challenge(db: AsyncSession = Depends(get_db)):
    today = date.today()
    result = await db.execute(
        select(MicrochallengeDefinition).where(
            and_(
                MicrochallengeDefinition.start_date <= today,
                (MicrochallengeDefinition.end_date.is_(None) | (MicrochallengeDefinition.end_date >= today))
            )
        ).order_by(MicrochallengeDefinition.start_date).limit(1)
    )
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="No active microchallenge found")
    return {
        "id": str(challenge.id),
        "week_number": challenge.week_number,  # ✅ added
        "title": challenge.title,
        "intro": challenge.intro,
        "instructions": challenge.instructions,
        "why": challenge.why,
        "tips": challenge.tips,
        "closing": challenge.closing,
        "start_date": challenge.start_date.isoformat(),
        "end_date": challenge.end_date.isoformat() if challenge.end_date else None,
    }


@router.get("/microchallenge/list")
async def get_challenge_list(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MicrochallengeDefinition).order_by(MicrochallengeDefinition.start_date)
    )
    challenges = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "title": c.title,
            "start_date": c.start_date.isoformat(),
            "end_date": c.end_date.isoformat() if c.end_date else None,
        }
        for c in challenges
    ]

from pydantic import BaseModel
from typing import Optional

class LogTodayRequest(BaseModel):
    challenge_id: uuid.UUID
    note: Optional[str] = ""

@router.post("/microchallenge/log")
async def log_today(
    payload: LogTodayRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    print("HIT NEW LOG ROUTE ✅")

    today = date.today()

    result = await db.execute(
        select(MicrochallengeLog).where(
            MicrochallengeLog.user_id == user_id,
            MicrochallengeLog.challenge_id == payload.challenge_id,
            MicrochallengeLog.log_date == today
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
        return {"message": "Already logged for today"}

    new_log = MicrochallengeLog(
        user_id=user_id,
        challenge_id=payload.challenge_id,
        log_date=today,
        note=payload.note or "",
        created_at=datetime.utcnow()
    )

    db.add(new_log)
    await db.commit()
    return {"message": "Log successful"}


from fastapi import Query
from uuid import UUID

@router.get("/microchallenge/progress")
async def get_progress(
    challenge_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user),
):
    try:
        challenge_uuid = UUID(challenge_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID")

    result = await db.execute(
        select(MicrochallengeLog).where(
            MicrochallengeLog.user_id == user_id,
            MicrochallengeLog.challenge_id == challenge_uuid
        ).order_by(MicrochallengeLog.log_date.desc())
    )

    logs = result.scalars().all()

    return {
        "completed_days": len(logs),
        "notes": [
            {"date": log.log_date.isoformat(), "note": log.note or ""}
            for log in logs
        ]
    }


@router.get("/microchallenge/{challenge_id:uuid}")
async def get_challenge_by_id(challenge_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MicrochallengeDefinition).where(MicrochallengeDefinition.id == challenge_id)
    )
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return {
        "id": str(challenge.id),
        "title": challenge.title,
        "intro": challenge.intro,
        "instructions": challenge.instructions,
        "why": challenge.why,
        "tips": challenge.tips,
        "closing": challenge.closing,
        "start_date": challenge.start_date.isoformat(),
        "end_date": challenge.end_date.isoformat() if challenge.end_date else None,
    }
