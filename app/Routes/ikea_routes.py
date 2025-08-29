# IKEA Worksheet Backend - FastAPI + Supabase Schema Plan + Endpoints (Corrected Payload Handling)

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, Boolean
from uuid import uuid4, UUID
from datetime import date, datetime
from app.database import get_db
from app.models import IkeaWorksheet, IkeaTracker, User
from app.utils.auth import get_current_user
from app.analytics.posthog_client import track_event

router = APIRouter()

# 1. Save new worksheet (installer submission)
@router.post("/ikea/worksheet")
async def save_worksheet(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    struggle: str = Body(...),
    identity: str = Body(...),
    knowledge: str = Body(...),
    environment: dict = Body(...),
    tinyAction: str = Body(...),
):
    await db.execute(
        update(IkeaWorksheet)
        .where(IkeaWorksheet.user_id == current_user.id, IkeaWorksheet.status == 'active')
        .values(status='completed')
    )

    worksheet = IkeaWorksheet(
        id=uuid4(),
        user_id=current_user.id,
        created_at=datetime.utcnow(),
        status='active',
        struggle=struggle,
        identity=identity,
        knowledge=knowledge,
        environment=environment,
        tiny_action=tinyAction
    )
    db.add(worksheet)
    await db.commit()
    track_event(str(current_user.id), "ikea_worksheet_saved", {"worksheet_id": str(worksheet.id)})
    return {"id": str(worksheet.id)}

# 2. Get current active worksheet (for tracker)
@router.get("/ikea/worksheet/active")
async def get_active_worksheet(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(IkeaWorksheet).where(IkeaWorksheet.user_id == current_user.id, IkeaWorksheet.status == 'active').limit(1)
    )
    worksheet = result.scalar_one_or_none()
    if not worksheet:
        raise HTTPException(status_code=404, detail="No active worksheet found")

    return {
        "id": str(worksheet.id),
        "identity": worksheet.identity,
        "tinyAction": worksheet.tiny_action,
        "environment": worksheet.environment,
        "knowledge": worksheet.knowledge,
    }

# 3. Toggle today's tracker log
@router.post("/ikea/tracker/{worksheet_id}/toggle")
async def toggle_tracker(
    worksheet_id: UUID,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db)
):
    date_str = body.get("date")
    if not date_str:
        raise HTTPException(status_code=400, detail="Date is required")

    toggle_date = date.fromisoformat(date_str)

    result = await db.execute(
        select(IkeaTracker).where(
            IkeaTracker.worksheet_id == worksheet_id,
            IkeaTracker.date == toggle_date
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.completed = not existing.completed
        await db.commit()
        track_event(None, "ikea_tracker_toggled", {"worksheet_id": str(worksheet_id), "completed": existing.completed})
        return {"completed": existing.completed}
    else:
        entry = IkeaTracker(
            id=uuid4(),
            worksheet_id=worksheet_id,
            date=toggle_date,
            completed=True,
            note=None
        )
        db.add(entry)
        await db.commit()
        track_event(None, "ikea_tracker_toggled", {"worksheet_id": str(worksheet_id), "completed": True})
        return {"completed": True}

# 4. Get tracker streak or history (optional)
@router.get("/ikea/tracker/{worksheet_id}/history")
async def get_tracker_history(worksheet_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(IkeaTracker).where(IkeaTracker.worksheet_id == worksheet_id).order_by(IkeaTracker.date)
    )
    entries = result.scalars().all()
    return [
        {
            "date": entry.date.isoformat(),
            "completed": entry.completed,
            "note": entry.note
        } for entry in entries
    ]

# 5. Add/edit tracker note for a date (optional)
@router.post("/ikea/tracker/{worksheet_id}/note")
async def add_note(worksheet_id: UUID, body: dict = Body(...), db: AsyncSession = Depends(get_db)):
    date_str = body.get("date")
    note = body.get("note")
    if not date_str or note is None:
        raise HTTPException(status_code=400, detail="Date and note required")

    result = await db.execute(
        select(IkeaTracker).where(IkeaTracker.worksheet_id == worksheet_id, IkeaTracker.date == date.fromisoformat(date_str))
    )
    entry = result.scalar_one_or_none()

    if entry:
        entry.note = note
    else:
        entry = IkeaTracker(
            id=uuid4(),
            worksheet_id=worksheet_id,
            date=date.fromisoformat(date_str),
            completed=False,
            note=note
        )
        db.add(entry)

    await db.commit()
    track_event(None, "ikea_note_added", {"worksheet_id": str(worksheet_id), "date": date_str})
    return {"success": True, "date": date_str, "note": note}

@router.get("/ikea/worksheet/history")
async def get_worksheet_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(IkeaWorksheet)
        .where(IkeaWorksheet.user_id == current_user.id, IkeaWorksheet.status == 'completed')
        .order_by(IkeaWorksheet.created_at.desc())
    )
    worksheets = result.scalars().all()
    return [
        {
            "id": str(w.id),
            "identity": w.identity,
            "tinyAction": w.tiny_action,
            "created_at": w.created_at.isoformat() if w.created_at else None
        } for w in worksheets
    ]

@router.get("/ikea/worksheet/{worksheet_id}")
async def get_worksheet_detail(
    worksheet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(IkeaWorksheet)
        .where(IkeaWorksheet.id == worksheet_id, IkeaWorksheet.user_id == current_user.id)
    )
    worksheet = result.scalar_one_or_none()
    if not worksheet:
        raise HTTPException(status_code=404, detail="Worksheet not found")

    return {
        "id": str(worksheet.id),
        "identity": worksheet.identity,
        "tinyAction": worksheet.tiny_action,
        "knowledge": worksheet.knowledge,
        "environment": worksheet.environment,
        "status": worksheet.status,
        "created_at": worksheet.created_at.isoformat() if worksheet.created_at else None
    }