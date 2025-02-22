# src/models/video.py
from enum import Enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from src.database import Base
from src.models.base import BaseMixin


class ScriptStatus(str, Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"


class DeploymentPackageExt(Base):
    """
    Temporary storage of deployment package prompt data until MySQL migration
    """
    __tablename__ = "deployment_package_extensions"

    deployment_package_id = Column(Integer, unique=True, nullable=False, primary_key=True)
    prompt_template = Column(String, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Script(Base, BaseMixin):
    __tablename__ = "scripts"

    student_deployment_id = Column(Integer, unique=True, nullable=False)
    raw_llm_response = Column(String, nullable=True)
    content = Column(String, nullable=True)
    scene_dialogue = Column(JSON, nullable=True)
    variables = Column(JSON, nullable=True)
    prompt_used = Column(String, nullable=False)
    status = Column(String, nullable=False, default=ScriptStatus.PENDING)


class Video(Base, BaseMixin):
    __tablename__ = "videos"

    student_deployment_id = Column(Integer, nullable=False)
    script_id = Column(UUID(as_uuid=True), ForeignKey("scripts.id"), nullable=False)
    heygen_video_id = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")