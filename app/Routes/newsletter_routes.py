from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import NewsletterSubscriber
from pydantic import BaseModel, EmailStr
from datetime import datetime

router = APIRouter()

class SubscribeRequest(BaseModel):
    email: EmailStr

@router.post("/subscribe")
async def subscribe(request: SubscribeRequest, db: AsyncSession = Depends(get_db)):
    # Check if already subscribed
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == request.email)
    )
    existing = result.scalar_one_or_none()

    if existing:
        return {"status": "already_subscribed"}

    # Add new subscriber
    subscriber = NewsletterSubscriber(email=request.email, created_at=datetime.utcnow())
    db.add(subscriber)
    await db.commit()
    return {"status": "subscribed"}
