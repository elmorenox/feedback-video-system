# src/models/schema.py
import uuid
from enum import Enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    ForeignKey,
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


class VideoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseMixin:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_on = Column(DateTime, default=datetime.utcnow)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Video(BaseMixin, Base):
    __tablename__ = "videos"
    student_deployment_id = Column(Integer, unique=True)
    synthesia_video_id = Column(String)
    video_url = Column(String)
    status = Column(SQLAlchemyEnum(VideoStatus))


class GradingData(BaseMixin, Base):
    __tablename__ = "grading_data"
    student_deployment_id = Column(Integer, unique=True)
    raw_data = Column(JSON)
    llm_response = Column(JSON)
    created_for_template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"))


class Template(BaseMixin, Base):
    __tablename__ = "templates"
    deployment_package_id = Column(Integer)
    synthesia_template_id = Column(String)
    variables = Column(JSON)
