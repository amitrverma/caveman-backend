# app/routers/microchallenges.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import (
    MicrochallengeDefinition,
    UserMicrochallenge,
    User,
    MicrochallengeLog,
)
from datetime import datetime, date
from uuid import UUID
from app.utils.auth import get_current_user  # ✅ returns a User object
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


@router.get("/")
async def list_challenges(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MicrochallengeDefinition).order_by(MicrochallengeDefinition.created_at)
    )
    challenges = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "title": c.title,
            "created_at": c.created_at.isoformat(),
        }
        for c in challenges
    ]



@router.get("/active")
async def get_active_challenge(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MicrochallengeDefinition).order_by(MicrochallengeDefinition.created_at.desc()).limit(1)
    )
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="No active microchallenge found")
    return {
        "id": str(challenge.id),
        "title": challenge.title,
        "intro": challenge.intro,
        "instructions": challenge.instructions,
        "why": challenge.why,
        "tips": challenge.tips,
        "closing": challenge.closing,
        "created_at": challenge.created_at.isoformat(),
    }


# 🔹 Assign challenge to user
@router.post("/assign/{challenge_id}")
async def assign_microchallenge(
    challenge_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),  # ✅ User object
):
    result = await db.execute(
        select(MicrochallengeDefinition).where(MicrochallengeDefinition.id == challenge_id)
    )
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    mapping = UserMicrochallenge(user_id=current_user.id, challenge_id=challenge_id)
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)

    return {
        "id": str(mapping.id),
        "challenge_id": str(mapping.challenge_id),
        "status": mapping.status,
        "started_at": mapping.started_at,
    }


# 🔹 Get my assigned challenges
@router.get("/my")
async def my_microchallenges(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserMicrochallenge, MicrochallengeDefinition)
        .join(MicrochallengeDefinition, UserMicrochallenge.challenge_id == MicrochallengeDefinition.id)
        .where(UserMicrochallenge.user_id == current_user.id)
    )

    rows = result.all()

    return [
        {
            # mapping fields
            "id": str(um.id),
            "challenge_id": str(um.challenge_id),
            "status": um.status,
            "started_at": um.started_at,
            "completed_at": um.completed_at,

            # definition fields
            "title": mc.title,
            "intro": mc.intro,
            "instructions": mc.instructions,
            "why": mc.why,
            "tips": mc.tips,
            "closing": mc.closing,
            "created_at": mc.created_at,
        }
        for um, mc in rows
    ]


# 🔹 Mark challenge as completed
@router.post("/complete/{challenge_id}")
async def complete_microchallenge(
    challenge_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserMicrochallenge).where(
            UserMicrochallenge.user_id == current_user.id,
            UserMicrochallenge.challenge_id == challenge_id,
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="Challenge not assigned to user")

    mapping.status = "completed"
    mapping.completed_at = datetime.utcnow()

    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)

    return {
        "id": str(mapping.id),
        "challenge_id": str(mapping.challenge_id),
        "status": mapping.status,
        "completed_at": mapping.completed_at,
    }


class LogTodayRequest(BaseModel):
    challenge_id: UUID
    note: Optional[str] = ""


@router.post("/log")
async def log_today(
    payload: LogTodayRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    result = await db.execute(
        select(MicrochallengeLog).where(
            MicrochallengeLog.user_id == current_user.id,
            MicrochallengeLog.challenge_id == payload.challenge_id,
            MicrochallengeLog.log_date == today,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"message": "Already logged for today"}

    new_log = MicrochallengeLog(
        user_id=current_user.id,
        challenge_id=payload.challenge_id,
        log_date=today,
        note=payload.note or "",
        created_at=datetime.utcnow(),
    )

    db.add(new_log)
    await db.commit()
    return {"message": "Log successful"}


@router.get("/progress")
async def get_progress(
    challenge_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        challenge_uuid = UUID(challenge_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID")

    result = await db.execute(
        select(MicrochallengeLog)
        .where(
            MicrochallengeLog.user_id == current_user.id,
            MicrochallengeLog.challenge_id == challenge_uuid,
        )
        .order_by(MicrochallengeLog.log_date.desc())
    )
    logs = result.scalars().all()
    return {
        "completed_days": len(logs),
        "notes": [
            {"date": log.log_date.isoformat(), "note": log.note or ""}
            for log in logs
        ],
    }


@router.get("/{challenge_id}")
async def get_challenge(
    challenge_id: UUID,
    db: AsyncSession = Depends(get_db),
):
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
        "created_at": challenge.created_at.isoformat(),
    }

