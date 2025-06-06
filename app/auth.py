from fastapi import APIRouter, Depends, HTTPException, status, Request
from firebase_admin import auth as firebase_auth, credentials, initialize_app
from app.models import User
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
firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
print("🔐 Firebase credentials loaded from environment.")

if firebase_creds_json:
    try:
        json_dict = json.loads(firebase_creds_json)
        print("🔍 Firebase project_id:", json_dict.get("project_id"))
        json_dict["private_key"] = json_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(json_dict)
        initialize_app(cred)
        print("✅ Firebase Admin SDK initialized.")
    except Exception as e:
        print("❌ Firebase Admin SDK initialization failed:", e)
        raise RuntimeError("Failed to initialize Firebase Admin SDK")
else:
    print("❌ FIREBASE_CREDENTIALS_JSON is missing.")
    raise RuntimeError("Missing Firebase credentials")


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

        # Check if user exists
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            print("🆕 New user detected. Creating in DB...")
            user = User(id=uuid.uuid4(), email=email, name=name)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print("✅ User created:", user.id)
        else:
            print("👤 Existing user found:", user.id)

        jwt_token = create_jwt(user.id)
        print("🎫 JWT token issued successfully.")
        return {"token": jwt_token, "user": {"name": user.name, "email": user.email}}

    except Exception as e:
        print("🔥 Firebase login failed:", e)
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
