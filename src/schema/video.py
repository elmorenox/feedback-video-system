# src/schema/video.py
from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

from src.schema.base import BaseResponse


# Base Models for API Responses
class TimeStampedModel(BaseModel):
    created_on: datetime
    updated_on: datetime


class DBModelBase(TimeStampedModel):
    id: UUID

    class Config:
        from_attributes = True


class CreateVideoRequest(BaseModel):
    student_deployment_id: int


class VideoData(DBModelBase):
    student_deployment_id: int
    script_id: UUID
    status: str
    heygen_video_id: Optional[str] = None
    video_url: Optional[str] = None

    class Config:
        from_attributes = True  # Enable ORM mode


class VideoResponse(BaseResponse[VideoData]):
    pass


class HeyGenVariable(BaseModel):
    pass


class HeyGenPayload(BaseModel):
    pass


class HeyGenVariableProperties(BaseModel):
    pass
