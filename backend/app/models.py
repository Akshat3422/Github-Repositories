import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    github_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False)
    avatar_url = Column(String, nullable=True)
    encrypted_access_token = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    repo_id = Column(String, nullable=False, index=True)
    repo_name = Column(String, nullable=False)
    repo_full_name = Column(String, nullable=False)
    repo_pushed_at = Column(String, nullable=False)  # Used for caching checks

    # Status and checkpointing
    status = Column(String, default="pending")  # pending, running, failed, done
    checkpoint = Column(String, default="none")  # none, agent1, agent2, agent3

    # Agent Outputs
    agent1_output = Column(JSONB, nullable=True)  # Repo intelligence summary
    agent2_output = Column(JSONB, nullable=True)  # Grounded insights
    agent3_output = Column(JSONB, nullable=True)  # Generated drafts

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Cost & Token Tracking
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    model_used = Column(JSONB, default=dict)  # Track models used per step

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="jobs")
