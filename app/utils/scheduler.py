from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.exc import OperationalError
import asyncio
import logging
from pytz import timezone

from app.database import AsyncSessionLocal
from app.utils.reminder_engine import (
    send_spot_pushes,
    send_microchallenge_pushes,
    send_daily_nudge
)
from app.Routes.notifications_routes import send_daily_nudge

# Setup logging for visibility in Azure logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("apscheduler")

# Initialize scheduler
scheduler = AsyncIOScheduler()
india_tz = timezone("Asia/Kolkata")

def start_scheduler():
    scheduler.add_job(run_behavioral_job, CronTrigger(hour=9, minute=0, timezone=india_tz), id="behavioral_job")
    scheduler.add_job(run_challenge_job, CronTrigger(hour=13, minute=0, timezone=india_tz), id="challenge_job")
    scheduler.add_job(run_spot_job, CronTrigger(hour=20, minute=0, timezone=india_tz), id="spot_job")
    scheduler.start()
    logger.info("✅ Scheduler started with behavioral (9AM), challenge (12PM), and spot (8PM) jobs")

# Robust safe DB wrapper
async def run_safe(task_func, name: str):
    for attempt in range(3):
        try:
            async with AsyncSessionLocal() as db:
                await task_func(db)
            logger.info(f"✅ Job '{name}' succeeded on attempt {attempt+1}")
            break
        except OperationalError as e:
            logger.warning(f"⚠️ Job '{name}' DB error on attempt {attempt+1}: {e}")
            await asyncio.sleep(3)
        except Exception as e:
            logger.exception(f"🔥 Unexpected error in job '{name}': {e}")
            break

# Individual job runners
async def run_spot_job():
    await run_safe(send_spot_pushes, "spot_push")

async def run_challenge_job():
    await run_safe(send_microchallenge_pushes, "microchallenge_push")

async def run_behavioral_job():
     await run_safe(send_daily_nudge, "daily_nudge")