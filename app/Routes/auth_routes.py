from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import User, Waitlist, Participant
from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,   # ✅ dependency
)
from pydantic import BaseModel, EmailStr
import uuid
import json
import os
from datetime import datetime

from firebase_admin import auth as firebase_auth, credentials, initialize_app
from app.analytics.posthog_client import track_event, identify_user

firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

if firebase_creds_json:
    try:
        json_dict = json.loads(firebase_creds_json)
        json_dict["private_key"] = json_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(json_dict)
        initialize_app(cred)
    except Exception as e:
        raise RuntimeError("Failed to initialize Firebase Admin SDK from JSON string") from e

elif firebase_creds_path and os.path.exists(firebase_creds_path):
    try:
        cred = credentials.Certificate(firebase_creds_path)
        initialize_app(cred)
    except Exception as e:
        raise RuntimeError("Failed to initialize Firebase Admin SDK from file") from e

else:
    raise RuntimeError(
        "Missing Firebase credentials: set either FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH"
    )

router = APIRouter()

class AuthRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/signup")
async def signup(req: AuthRequest, db: AsyncSession = Depends(get_db)):
    # check if user exists
    result = await db.execute(select(User).where(User.email == req.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=req.email,
        password_hash=hash_password(req.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    identify_user(str(user.id), {"email": user.email})
    track_event(str(user.id), "user_signup")
    return {"token": token, "user": {"id": str(user.id), "email": user.email}}

@router.post("/login")
async def login(req: AuthRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    track_event(str(user.id), "user_login")
    return {"token": token, "user": {"id": str(user.id), "email": user.email}}

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
    }


@router.post("/firebase-login")
async def firebase_login(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
        id_token = body.get("idToken")

        decoded_token = firebase_auth.verify_id_token(id_token)
        email = decoded_token["email"]
        name = decoded_token.get("name", "Anonymous")
        google_id = decoded_token.get("uid")

        stmt = select(Participant).where(Participant.email == email)
        result = await db.execute(stmt)
        participant = result.scalars().first()

        if participant:
            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            user = result.scalars().first()

            if not user:
                user = User(id=uuid.uuid4(), email=email, name=name, google_id=google_id)
                db.add(user)
                await db.commit()
                await db.refresh(user)

            if user and not user.google_id:
                user.google_id = google_id
                await db.commit()
                await db.refresh(user)

            jwt_token = create_access_token({"sub": str(user.id)})
            # identify_user(str(user.id), {"email": user.email, "name": user.name})
            track_event(str(user.id), "user_login", {"method": "firebase"})
            return {
                "token": jwt_token,
                "user": {"id": str(user.id), "name": user.name, "email": user.email}
            }

        else:
            stmt = select(Waitlist).where(Waitlist.email == email)
            result = await db.execute(stmt)
            existing = result.scalars().first()

            if not existing:
                waitlist_entry = Waitlist(email=email, name=name)
                db.add(waitlist_entry)
                await db.commit()

            track_event(email, "firebase_preview")
            return {
                "token": None,
                "user": {"name": name, "email": email},
                "preview": True
            }

    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
