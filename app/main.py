from fastapi import FastAPI
from app import database, auth, routes
from app.Routes import webpush_routes, notifications_routes, ikea_routes, reflections_routes
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
        "https://caveman.amitrverma.com",
        "https://amitrverma.com",
        "http://localhost:3000", 
        "https://neurocientwa-akaybxbygyc8bgeg.canadacentral-01.azurewebsites.net",
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
app.include_router(auth.router, prefix="/auth")
app.include_router(routes.router, prefix="/api")
app.include_router(webpush_routes.router, prefix="/api")
app.include_router(notifications_routes.router, prefix="/api")
app.include_router(ikea_routes.router, prefix="/api", tags=["ikea"])
app.include_router(reflections_routes.router, prefix="/api", tags=["reflections"])
