from fastapi import FastAPI
from app import database, auth, routes
from app.Routes import webpush_routes
from app.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware

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

# ✅ Mount routers (perfect mounting structure)
app.include_router(auth.router, prefix="/auth")
app.include_router(routes.router, prefix="/api")
app.include_router(webpush_routes.router, prefix="/api")