from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import CavemanSpot
from app.schemas import SpotCreate, SpotResponse
from datetime import datetime, date
import uuid
import jwt
from app.config import settings

router = APIRouter()

FAKE_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")  # TODO: Replace with real user from JWT

def get_current_user(authorization: str = Header(...)):
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid auth scheme")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or missing token")


@router.post("/spots", response_model=SpotResponse)
async def create_spot(
    spot: SpotCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
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


@router.get("/spots", response_model=list[SpotResponse])
async def get_spots(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    result = await db.execute(
        CavemanSpot.__table__.select().where(CavemanSpot.user_id == user_id).order_by(CavemanSpot.date.desc())
    )
    return result.fetchall()

