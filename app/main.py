from fastapi import FastAPI
from app import database
from app.Routes import (
    webpush_routes,
    notifications_routes,
    ikea_routes,
    reflections_routes,
    whatsapp_routes,
    newsletter_routes,
    auth_routes,
    article_routes,
    challenge_routes,
    spot_routes,
    nudge_routes,
    preferences_route
)
from app.database import Base, engine
from app.utils.scheduler import start_scheduler 
from fastapi.middleware.cors import CORSMiddleware
import openai
import os

# ✅ Set OpenAI API key globally
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("OpenAI API key not set. Please define OPENAI_API_KEY in environment.")

app = FastAPI()

# ✅ CORS setup (safe for both local & prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.neurocient.com",
        "https://neurocient.com",
        "http://localhost:3000", 
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ DB initialization on startup
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler()  # ✅ Start APScheduler

# ✅ Mount routers (perfect mounting structure)
app.include_router(webpush_routes.router, prefix="/api")
app.include_router(notifications_routes.router, prefix="/api")
app.include_router(ikea_routes.router, prefix="/api", tags=["ikea"])
app.include_router(reflections_routes.router, prefix="/api", tags=["reflections"])
app.include_router(whatsapp_routes.router, prefix="/wa", tags=["whatsapp"])  # or "/wa" if you want a namespace
app.include_router(newsletter_routes.router, prefix="/api", tags=["newsletter"])
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(article_routes.router, prefix="/articles", tags=["saved"])
app.include_router(challenge_routes.router, prefix="/challenges", tags=["microchallenge"])
app.include_router(spot_routes.router, prefix="/api", tags=["spots"])
app.include_router(nudge_routes.router, prefix="/api", tags=["nudges"])
app.include_router(preferences_route.router, prefix="/user", tags=["preferences"])