from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import UserPreferences, User
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/preferences")
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")

    return {
        "id": str(prefs.id),
        "user_id": str(prefs.user_id),
        "nudge_enabled": prefs.nudge_enabled,
        "microchallenge_enabled": prefs.microchallenge_enabled,
        "notif_channel": prefs.notif_channel,
        "whatsapp_number": prefs.whatsapp_number,
        "whatsapp_verified": prefs.whatsapp_verified,
    }


@router.patch("/preferences")
async def update_preferences(
    updates: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")

    for field, value in updates.items():
        if hasattr(prefs, field):
            setattr(prefs, field, value)

    db.add(prefs)
    await db.commit()
    await db.refresh(prefs)

    return {
        "id": str(prefs.id),
        "user_id": str(prefs.user_id),
        "nudge_enabled": prefs.nudge_enabled,
        "microchallenge_enabled": prefs.microchallenge_enabled,
        "notif_channel": prefs.notif_channel,
        "whatsapp_number": prefs.whatsapp_number,
        "whatsapp_verified": prefs.whatsapp_verified,
    }
