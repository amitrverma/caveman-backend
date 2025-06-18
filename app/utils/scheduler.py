from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import get_db
from app.utils.reminder_engine import (
    send_spot_pushes,
    send_microchallenge_pushes
)
from app.Routes.notifications_routes import send_daily_nudge

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(run_behavioral_job, CronTrigger(hour=9, minute=0))      # 9 AM behavioral nudge
    scheduler.add_job(run_challenge_job, CronTrigger(hour=12, minute=0))      # 12 PM microchallenge
    scheduler.add_job(run_spot_job, CronTrigger(hour=20, minute=0))           # 8 PM caveman spot
    scheduler.start()

async def run_spot_job():
    async for db in get_db():
        await send_spot_pushes(db)

async def run_challenge_job():
    async for db in get_db():
        await send_microchallenge_pushes(db)

async def run_behavioral_job():
    async for db in get_db():
        await send_daily_nudge(db)
