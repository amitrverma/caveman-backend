from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from app.models import WebPushSubscription, User
from app.database import get_db
from app.utils.auth import get_current_user

router = APIRouter()

@router.post("/register-webpush")
async def register_webpush(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    endpoint = payload.get("endpoint")
    keys = payload.get("keys")

    if not endpoint or not keys:
        raise HTTPException(status_code=400, detail="Missing endpoint or keys")

    # Check if subscription already exists
    stmt = select(WebPushSubscription).where(WebPushSubscription.endpoint == endpoint)
    result = await db.execute(stmt)
    existing = result.scalars().first()

    if not existing:
        new_sub = WebPushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            keys=keys,
        )
        db.add(new_sub)
        await db.commit()

    return {"status": "ok"}


@router.post("/unregister-webpush")
async def unregister_webpush(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        stmt = delete(WebPushSubscription).where(WebPushSubscription.user_id == current_user.id)
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unregister subscription: {str(e)}")

    return {"status": "removed"}
