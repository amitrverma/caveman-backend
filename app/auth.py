from fastapi import APIRouter, Depends, HTTPException, status, Request
from firebase_admin import auth as firebase_auth, credentials, initialize_app
from app.models import User, Waitlist, Participant
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
import uuid
import jwt
import json
import os
import io
from sqlalchemy import select
from datetime import datetime, timedelta

router = APIRouter()

# Init Firebase Admin with logging
import os
import json
from firebase_admin import credentials, initialize_app

firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")

if firebase_creds_json:
    print("🔐 Firebase credentials loaded from JSON string.")
    try:
        json_dict = json.loads(firebase_creds_json)
        json_dict["private_key"] = json_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(json_dict)
        initialize_app(cred)
        print("✅ Firebase Admin SDK initialized using inline JSON.")
    except Exception as e:
        print("❌ Firebase initialization from JSON string failed:", e)
        raise RuntimeError("Failed to initialize Firebase Admin SDK from JSON string")

elif firebase_creds_path and os.path.exists(firebase_creds_path):
    print(f"🔐 Firebase credentials loaded from file: {firebase_creds_path}")
    try:
        cred = credentials.Certificate(firebase_creds_path)
        initialize_app(cred)
        print("✅ Firebase Admin SDK initialized using file path.")
    except Exception as e:
        print("❌ Firebase initialization from file failed:", e)
        raise RuntimeError("Failed to initialize Firebase Admin SDK from file")

else:
    print("❌ Firebase credentials not found in environment.")
    raise RuntimeError("Missing Firebase credentials: set either FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH")


# JWT creation helper
def create_jwt(user_id):
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    print("🔑 Creating JWT for user_id:", user_id)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


@router.post("/firebase-login")
async def firebase_login(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
        id_token = body.get("idToken")
        print("📥 Received ID token:", id_token[:40], "...")

        decoded_token = firebase_auth.verify_id_token(id_token)
        print("🧠 Decoded Firebase token:", decoded_token)

        email = decoded_token["email"]
        name = decoded_token.get("name", "Anonymous")
        print(f"👤 Firebase user: {email}, {name}")

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
                print("🆕 Creating user from participant list...")
                user = User(id=uuid.uuid4(), email=email, name=name)
                db.add(user)
                await db.commit()
                await db.refresh(user)

            jwt_token = create_jwt(user.id)
            print("🎫 JWT token issued successfully.")
            return {
                "token": jwt_token,
                "user": { "id": str(user.id),"name": user.name, "email": user.email}
            }

        else:
            # Not a participant → add to waitlist if not already there
            print("👀 Not a participant — handling waitlist flow...")
            stmt = select(Waitlist).where(Waitlist.email == email)
            result = await db.execute(stmt)
            existing = result.scalars().first()

            if not existing:
                waitlist_entry = Waitlist(email=email, name=name)
                db.add(waitlist_entry)
                await db.commit()
                print("📝 Added to waitlist.")

            return {
                "token": None,
                "user": {"name": name, "email": email},
                "preview": True
            }

    except Exception as e:
        print("🔥 Firebase login failed:", e)
        raise HTTPException(status_code=401, detail="Invalid Firebase token")