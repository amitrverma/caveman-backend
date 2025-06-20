import random
from fastapi import HTTPException   
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select    
from app.models import BehavioralNudge

async def get_random_active_nudge(db: AsyncSession) -> BehavioralNudge:
    result = await db.execute(
        select(BehavioralNudge).where(BehavioralNudge.is_active == True)
    )
    nudges = result.scalars().all()

    if not nudges:
        raise HTTPException(status_code=404, detail="No active nudges available")

    return random.choice(nudges)
