from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import CavemanSpot, User
from app.utils.auth import get_current_user
from pydantic import BaseModel
from datetime import date, datetime
import uuid

router = APIRouter(prefix="/spots")

class SpotCreate(BaseModel):
    description: str
    date: date | None = None

class SpotResponse(BaseModel):
    id: uuid.UUID
    description: str
    date: date
    created_at: datetime

    class Config:
        orm_mode = True

@router.post("/", response_model=SpotResponse)
async def create_spot(
    spot: SpotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        new_spot = CavemanSpot(
            user_id=current_user.id,
            description=spot.description,
            date=spot.date or date.today(),
            created_at=datetime.utcnow(),
        )
        db.add(new_spot)
        await db.commit()
        await db.refresh(new_spot)
        return new_spot
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create spot: {e}")

@router.get("/", response_model=list[SpotResponse])
async def get_spots(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(CavemanSpot)
            .where(CavemanSpot.user_id == current_user.id)
            .order_by(CavemanSpot.date.desc())
        )
        spots = result.scalars().all()
        return list(spots)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
