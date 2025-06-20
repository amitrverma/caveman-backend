from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Date, JSON, UniqueConstraint, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class CavemanSpot(Base):
    __tablename__ = "spots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    description = Column(Text)
    date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Participant(Base):
    __tablename__ = "participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    phone_number = Column(String, nullable=True)
    cohort = Column(String, nullable=True)
    joined_on = Column(DateTime, default=datetime.utcnow)    

class MicrochallengeDefinition(Base):
    __tablename__ = "microchallenge_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_number = Column(Integer, nullable=False, unique=True)  # ✅ New field added
    title = Column(Text, nullable=False)
    intro = Column(JSON, nullable=False)           # Array of paragraphs
    instructions = Column(JSON, nullable=False)    # Array of steps
    why = Column(Text, nullable=False)
    tips = Column(JSON, nullable=False)            # Array of tips
    closing = Column(Text, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)



class MicrochallengeLog(Base):
    __tablename__ = "microchallenge_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    challenge_id = Column(UUID(as_uuid=True), ForeignKey("microchallenge_definitions.id"), nullable=False)
    log_date = Column(Date, nullable=False)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", "log_date", name="uq_user_challenge_date"),
    )    

class WebPushSubscription(Base):
    __tablename__ = "web_push_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    endpoint = Column(Text, nullable=False, unique=True)
    keys = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class IkeaWorksheet(Base):
    __tablename__ = "ikea_worksheet"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="active")  # 'active' or 'completed'
    struggle = Column(Text, nullable=False)
    identity = Column(Text, nullable=False)
    knowledge = Column(Text, nullable=False)
    environment = Column(JSON, nullable=False)  # { easier: "", harder: "" }
    tiny_action = Column(Text, nullable=False)

    user = relationship("User", backref="ikea_worksheets")
    tracker_entries = relationship("IkeaTracker", back_populates="worksheet", cascade="all, delete-orphan")


class IkeaTracker(Base):
    __tablename__ = "ikea_tracker"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worksheet_id = Column(UUID(as_uuid=True), ForeignKey("ikea_worksheet.id"), nullable=False)
    date = Column(Date, nullable=False)
    completed = Column(Boolean, nullable=False, default=False)
    note = Column(Text)

    worksheet = relationship("IkeaWorksheet", back_populates="tracker_entries")

    __table_args__ = (
        UniqueConstraint("worksheet_id", "date", name="uq_worksheet_date"),
    )

class BehavioralNudge(Base):
    __tablename__ = "behavioral_nudges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title = Column(String, nullable=True)             # Optional, e.g. "💡 Nudge of the Day"
    paragraphs = Column(JSON, nullable=False)         # Array of paragraph strings
    quote = Column(Text, nullable=True)               # Highlighted quote block
    link = Column(String, nullable=True)              # Optional blog/article/resource URL
    is_active = Column(Boolean, default=True)         # Only active nudges are served
    created_at = Column(DateTime, default=datetime.utcnow)    

class WeeklyReflection(Base):
    __tablename__ = "weekly_reflections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)