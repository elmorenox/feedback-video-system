# src/models/schema.py
import uuid
from enum import Enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    Float,
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


class VideoStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScoreType(str, Enum):
    OVERALL = "overall"
    COMPONENT = "component"
    SUBCOMPONENT = "subcomponent"


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


class ScoreRange(BaseMixin, Base):
    __tablename__ = "score_ranges"
    name = Column(String)
    min_score = Column(Float)
    max_score = Column(Float)


class Template(BaseMixin, Base):
    __tablename__ = "templates"
    deployment_package_id = Column(Integer)  # Links to workload
    synthesia_template_id = Column(String)  # ID from Synthesia studio
    variables = Column(JSON)  # Maps Synthesia vars to our data fields


class TemplateContent(BaseMixin, Base):
    __tablename__ = "template_contents"
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"))
    score_range_id = Column(UUID(as_uuid=True), ForeignKey("score_ranges.id"))
    variable_name = Column(String)  # Which Synthesia variable this maps to
    content = Column(String)  # Text with our placeholders
    score_type = Column(SQLAlchemyEnum(ScoreType))
