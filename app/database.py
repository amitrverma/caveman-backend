from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False, # Set to True for debugging, False for production
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    pool_pre_ping=True, # Ensures connections are alive before using them
    pool_timeout=30,
)

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
