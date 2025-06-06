from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import uuid

class SpotCreate(BaseModel):
    description: str
    date: Optional[date] = None

class SpotResponse(BaseModel):
    id: uuid.UUID
    description: str
    date: date
    created_at: datetime

    class Config:
        orm_mode = True
