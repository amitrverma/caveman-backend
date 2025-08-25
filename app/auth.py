from fastapi import APIRouter, Depends, HTTPException, Request
from firebase_admin import auth as firebase_auth, credentials, initialize_app
from app.models import User, Waitlist, Participant
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import json
import os
from datetime import datetime

# ✅ Use the same JWT machinery
from app.utils.auth import create_access_token  

router = APIRouter()

# --- Firebase init ---
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
    raise RuntimeError("Missing Firebase credentials: set either FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH")


@router.post("/firebase-login")
async def firebase_login(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
        id_token = body.get("idToken")

        decoded_token = firebase_auth.verify_id_token(id_token)
        email = decoded_token["email"]
        name = decoded_token.get("name", "Anonymous")
        google_id = decoded_token.get("uid")

        # Step 1: Check if email is in participants
        stmt = select(Participant).where(Participant.email == email)
        result = await db.execute(stmt)
        participant = result.scalars().first()

        if participant:
            # Step 2: Check if user already exists in `users`
            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            user = result.scalars().first()

            if not user:
                user = User(id=uuid.uuid4(), email=email, name=name, google_id=google_id)
                db.add(user)
                await db.commit()
                await db.refresh(user)

            if user and not user.google_id:
                print(f"⚡ Updating google_id for {email}")
                user.google_id = google_id
                await db.commit()
                await db.refresh(user)

            # ✅ Use the unified token helper
            jwt_token = create_access_token({"sub": str(user.id)})
            return {
                "token": jwt_token,
                "user": {"id": str(user.id), "name": user.name, "email": user.email}
            }

        else:
            # Not a participant → add to waitlist if not already there
            stmt = select(Waitlist).where(Waitlist.email == email)
            result = await db.execute(stmt)
            existing = result.scalars().first()

            if not existing:
                waitlist_entry = Waitlist(email=email, name=name)
                db.add(waitlist_entry)
                await db.commit()

            return {
                "token": None,
                "user": {"name": name, "email": email},
                "preview": True
            }

    except Exception as e:
        print("🔥 Firebase login failed:", e)
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
