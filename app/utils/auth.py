from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import User
import os
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ------------------------
# Config
# ------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

ENV = os.getenv("ENV", "dev")

# Domain setup
raw_domain = os.getenv("COOKIE_DOMAIN", None)
COOKIE_DOMAIN = None if raw_domain in (None, "None", "localhost") else raw_domain

# Cookie flags
if ENV == "prod":
    COOKIE_SECURE = True
    COOKIE_SAMESITE = "None"
else:  # local dev
    COOKIE_SECURE = False
    COOKIE_SAMESITE = "Lax"

# ------------------------
# Password hashing
# ------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ------------------------
# JWT handling
# ------------------------
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "typ": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": user_id, "exp": expire, "typ": "refresh"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

# ------------------------
# Cookie helpers
# ------------------------
def set_auth_cookies(resp: Response, user_id: str):
    """Set access + refresh + session hint cookies."""
    access = create_access_token({"sub": user_id})
    refresh = create_refresh_token(user_id)

    resp.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    resp.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    resp.set_cookie(
        key="session_present",  # readable by frontend/middleware
        value="1",
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        path="/",
    )
    return access, refresh

def clear_auth_cookies(resp: Response):
    """Clear all auth cookies."""
    for key in ["access_token", "refresh_token", "session_present"]:
        resp.delete_cookie(key, domain=COOKIE_DOMAIN, path="/")

def get_token_from_cookies(req: Request) -> Optional[str]:
    return req.cookies.get("access_token")

# ------------------------
# Security dependency
# ------------------------
security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    req: Request = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract the current user either from Bearer token OR HttpOnly cookie.
    """

    token = None

    # 1) Prefer Authorization header
    if credentials:
        token = credentials.credentials
    # 2) Fallback to HttpOnly cookie
    elif req:
        token = get_token_from_cookies(req)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # Fetch user from DB
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return user

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")
