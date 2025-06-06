from fastapi import FastAPI
from app import database, auth, routes
from app.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
        allow_origins=[
        "https://caveman.amitrverma.com",
        "https://amitrverma.com",
        "http://localhost:3000", 
        "https://neurocientwa-akaybxbygyc8bgeg.canadacentral-01.azurewebsites.net", # for local dev (optional)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(auth.router, prefix="/auth")
app.include_router(routes.router)
