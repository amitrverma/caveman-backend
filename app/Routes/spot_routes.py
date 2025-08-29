from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import CavemanSpot, User
from app.utils.auth import get_current_user
from datetime import date, datetime
import uuid
from app.analytics.posthog_client import track_event

router = APIRouter(prefix="/spots")

@router.post("/")
async def create_spot(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        body = await request.json()
        description = body.get("description")
        spot_date = body.get("date")

        if not description:
            raise HTTPException(status_code=400, detail="Description is required")

        new_spot = CavemanSpot(
            user_id=current_user.id,
            description=description,
            date=date.fromisoformat(spot_date) if spot_date else date.today(),
            created_at=datetime.utcnow(),
        )
        db.add(new_spot)
        await db.commit()
        await db.refresh(new_spot)
        track_event(str(current_user.id), "spot_created")

        return {
            "id": str(new_spot.id),
            "description": new_spot.description,
            "date": new_spot.date,
            "created_at": new_spot.created_at,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create spot: {e}")


@router.get("/")
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

        return [
            {
                "id": str(s.id),
                "description": s.description,
                "date": s.date,
                "created_at": s.created_at,
            }
            for s in spots
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
