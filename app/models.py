from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Date, JSON, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID
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