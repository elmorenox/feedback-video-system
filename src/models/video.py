# src/models/video.py
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    JSON,
    ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database import Base
from src.models.base import BaseMixin
from src.schema.video import VideoStatus, ScriptStatus


class DeploymentPackageExt(Base):
    """
    Extends deployment packages from MySQL with additional fields in SQLite
    """

    __tablename__ = "deployment_package_extensions"

    deployment_package_id = Column(
        Integer, unique=True, nullable=False, primary_key=True
    )
    heygen_template_id = Column(
        Integer, ForeignKey("heygen_templates.id"), nullable=True
    )
    prompt_template = Column(String, nullable=False)
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_on = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationship to the local SQLite table
    heygen_template = relationship(
        "HeyGenTemplate",
        backref="package_extensions"
    )


class Script(Base, BaseMixin):
    __tablename__ = "scripts"

    student_deployment_id = Column(Integer, unique=True, nullable=False)
    prompt_used = Column(String, nullable=False)
    scene_dialogue = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default=ScriptStatus.PENDING)


# TODO: Add heygen submission date to video
class Video(Base, BaseMixin):
    __tablename__ = "videos"

    student_deployment_id = Column(Integer, nullable=False)
    script_id = Column(UUID(as_uuid=True), ForeignKey("scripts.id"), nullable=False)
    heygen_video_id = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    status = Column(String, nullable=False, default=VideoStatus.PENDING)
    callback_id = Column(String, nullable=True)


class HeyGenTemplate(Base, BaseMixin):
    __tablename__ = "heygen_templates"

    template_id = Column(String, nullable=False, comment="HeyGen API template ID")
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    variable_mappings = Column(JSON, nullable=True, default=lambda: {"mappings": []})
