from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.helper.common import get_random_active_nudge

router = APIRouter(prefix="/nudges")

@router.get("/random")
async def get_random_nudge(db: AsyncSession = Depends(get_db)):
    nudge = await get_random_active_nudge(db)
    return {
        "id": str(nudge.id),
        "title": nudge.title,
        "paragraphs": nudge.paragraphs,
        "quote": nudge.quote,
        "link": nudge.link,
    }
