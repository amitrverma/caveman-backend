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
from datetime import datetime, timedelta

router = APIRouter()

# Init Firebase Admin
firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

if firebase_creds_json:
    cred = credentials.Certificate(json.loads(firebase_creds_json))
    initialize_app(cred)
else:
    raise RuntimeError("Missing Firebase credentials")

# Issue JWT using your SECRET_KEY
def create_jwt(user_id):
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

@router.post("/firebase-login")
async def firebase_login(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    id_token = body.get("idToken")

    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        email = decoded_token["email"]
        name = decoded_token.get("name", "Anonymous")

        # Check if user exists
        result = await db.execute(
            User.__table__.select().where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(id=uuid.uuid4(), email=email, name=name)
            db.add(user)
            await db.commit()
            await db.refresh(user)

        jwt_token = create_jwt(user.id)
        return {"token": jwt_token, "user": {"name": user.name, "email": user.email}}

    except Exception as e:
        print("Firebase token verification failed:", e)
        raise HTTPException(status_code=401, detail="Invalid Firebase token")

