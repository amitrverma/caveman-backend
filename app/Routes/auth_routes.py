from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.responses import JSONResponse
from app.database import get_db
from app.models import User, Waitlist, Participant, UserPreferences
from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    set_auth_cookies,
    clear_auth_cookies,
)
from pydantic import BaseModel, EmailStr
import uuid
import json
import os
from jose import jwt, JWTError

from firebase_admin import auth as firebase_auth, credentials, initialize_app, exceptions
from app.analytics.posthog_client import track_event, identify_user

# ---------------- Firebase init ----------------
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
    raise RuntimeError("Missing Firebase credentials")

# ---------------- Router ----------------
router = APIRouter()

class AuthRequest(BaseModel):
    email: EmailStr
    password: str

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key")
ALGORITHM = "HS256"

# ---------------- Signup ----------------
@router.post("/signup")
async def signup(req: AuthRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(id=uuid.uuid4(), email=req.email, password_hash=hash_password(req.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # ✅ Create default preferences row
    prefs = UserPreferences(user_id=user.id)
    db.add(prefs)
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    response = JSONResponse(
        content={"token": token, "user": {"id": str(user.id), "email": user.email}}
    )
    set_auth_cookies(response, str(user.id))

    identify_user(str(user.id), {"email": user.email})
    track_event(str(user.id), "user_signup")

    return response

# ---------------- Login ----------------
@router.post("/login")
async def login(req: AuthRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    response = JSONResponse(
        content={"token": token, "user": {"id": str(user.id), "email": user.email}}
    )
    set_auth_cookies(response, str(user.id))

    track_event(str(user.id), "user_login")
    return response

# ---------------- Me ----------------
@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
    }

# ---------------- Refresh ----------------
@router.post("/refresh")
async def refresh(req: Request, db: AsyncSession = Depends(get_db)):
    rt = req.cookies.get("refresh_token")
    if not rt:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        payload = jwt.decode(rt, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("typ") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh")

    # ✅ Fetch user details from DB
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ✅ Issue new cookies
    access, _ = set_auth_cookies(JSONResponse(content={}), user_id)

    # ✅ Build consistent response
    response = JSONResponse(
        content={
            "token": access,
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
            },
        }
    )
    set_auth_cookies(response, user_id)

    return response


# ---------------- Logout ----------------
@router.post("/logout")
async def logout():
    response = JSONResponse(content={"ok": True})
    clear_auth_cookies(response)
    return response

# ---------------- Firebase Login ----------------
@router.post("/firebase-login")
async def firebase_login(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
        id_token = body.get("idToken")
        if not id_token:
            raise HTTPException(status_code=400, detail="Missing idToken")

        try:
            decoded_token = firebase_auth.verify_id_token(id_token, clock_skew_seconds=60)
        except exceptions.InvalidIdTokenError:
            raise HTTPException(status_code=401, detail="Invalid Firebase token")
        except exceptions.ExpiredIdTokenError:
            raise HTTPException(status_code=401, detail="Expired Firebase token")
        except Exception:
            raise HTTPException(status_code=401, detail="Firebase verification failed")

        email = decoded_token["email"]
        name = decoded_token.get("name", "Anonymous")
        google_id = decoded_token.get("uid")

        # Ensure participant exists
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

                    # ✅ Create default preferences row
                prefs = UserPreferences(user_id=user.id)
                db.add(prefs)
                await db.commit()
                
            if user and not user.google_id:
                user.google_id = google_id
                await db.commit()
                await db.refresh(user)

            jwt_token = create_access_token({"sub": str(user.id)})
            response = JSONResponse(
                content={
                    "token": jwt_token,
                    "user": {"id": str(user.id), "name": user.name, "email": user.email},
                }
            )
            set_auth_cookies(response, str(user.id))

            track_event(str(user.id), "user_login", {"method": "firebase"})
            return response

        # If not participant, put on waitlist
        stmt = select(Waitlist).where(Waitlist.email == email)
        result = await db.execute(stmt)
        existing = result.scalars().first()

        if not existing:
            waitlist_entry = Waitlist(email=email, name=name)
            db.add(waitlist_entry)
            await db.commit()

        track_event(email, "firebase_preview")
        return JSONResponse(
            content={"token": None, "user": {"name": name, "email": email}, "preview": True}
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Server error during Firebase login")
