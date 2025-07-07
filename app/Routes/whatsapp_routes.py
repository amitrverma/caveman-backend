import logging
from fastapi import APIRouter, Request, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime, date
from fastapi.responses import JSONResponse


import os
import requests

from app.database import get_db
from app.models import User, CavemanSpot

router = APIRouter()
logger = logging.getLogger("whatsapp")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        form = await request.form()
        logger.info("📩 WhatsApp Form payload: %s", dict(form))

        from_number = form.get("From", "").replace("whatsapp:", "").strip()
        message_body = form.get("Body", "").strip()

        logger.info("📱 From: %s | Message: %s", from_number, message_body)

        if not message_body.lower().startswith("spot:"):
            logger.info("⛔ Ignored message (not a Spot): %s", message_body)
            return JSONResponse({"status": "ignored", "message": "Not a Caveman Spot message"})

        description = message_body[5:].strip()

        result = await db.execute(select(User).where(User.phone_number == from_number))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("❌ No user found for phone number: %s", from_number)
            return JSONResponse(
                {"status": "error", "message": f"No user found with phone: {from_number}"},
                status_code=404
            )

        spot = CavemanSpot(
            id=uuid4(),
            user_id=user.id,
            description=description,
            date=date.today(),
            created_at=datetime.utcnow()
        )
        db.add(spot)
        await db.commit()

        # Send auto-reply
        status, response = send_whatsapp_message(from_number, "🔥 Got it. Your caveman has been spotted and logged. Nice awareness!")
        logger.info("📤 Auto-reply sent to %s | Status: %s", from_number, status)


        logger.info("✅ Spot logged for user %s (%s)", user.name, from_number)
        return JSONResponse({"status": "ok", "message": "🧠 Caveman Spot logged successfully"})

    except Exception as e:
        logger.exception("🔥 Error processing WhatsApp message: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


def send_whatsapp_message(to_number: str, message: str) -> bool:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    data = {
        "From": from_number,
        "To": f"whatsapp:{to_number}",
        "Body": message,
    }

    try:
        response = requests.post(url, data=data, auth=(account_sid, auth_token))
        if response.status_code == 201:
            logger.info("✅ WhatsApp message sent to %s", to_number)
            return True
        else:
            logger.warning("⚠️ Failed to send WhatsApp message to %s | %s", to_number, response.text)
            return False
    except Exception as e:
        logger.exception("🔥 Error sending WhatsApp message to %s", to_number)
        return False
