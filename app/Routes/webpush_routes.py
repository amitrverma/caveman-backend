from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select  # ✅ ORM queries
from app.models import WebPushSubscription
from app.database import get_db

import uuid

router = APIRouter()

# ✅ Pydantic model for incoming request
class WebPushSubscriptionIn(BaseModel):
    user_id: str
    endpoint: str
    keys: dict

@router.post("/register-webpush")
async def register_webpush(sub: WebPushSubscriptionIn, db: AsyncSession = Depends(get_db)):
    # Use SQLAlchemy ORM select instead of raw SQL
    stmt = select(WebPushSubscription).where(WebPushSubscription.endpoint == sub.endpoint)
    result = await db.execute(stmt)
    existing = result.scalars().first()

    if not existing:
        new_sub = WebPushSubscription(
            user_id=uuid.UUID(sub.user_id),
            endpoint=sub.endpoint,
            keys=sub.keys
        )
        db.add(new_sub)
        await db.commit()

    return {"status": "ok"}
