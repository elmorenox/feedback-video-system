# src/schema/video.py
from typing import Any, Dict
from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel
from enum import Enum

from src.schema.base import BaseResponse


class VideoStatus(str, Enum):
    # Status that HeyGen provides
    # Not submitted is not a HeyGen status,
    # but a status we use to indicate that the video has not been submitted.
    NOT_SUBMITTED = "not_submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"


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


class HeyGenResponseData(BaseModel):
    success: bool
    video_id: Optional[str] = None
    status: Optional[str] = None
    video_url: Optional[str] = None
    created_at: Optional[int] = None
    error: Optional[str] = None
    response: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class VideoData(DBModelBase):
    student_deployment_id: int
    script_id: UUID
    status: VideoStatus
    heygen_video_id: Optional[str] = None
    video_url: Optional[str] = None
    heygen_response: Optional[HeyGenResponseData] = None

    class Config:
        from_attributes = True


class VideoResponse(BaseResponse[VideoData]):
    pass


class HeyGenVariableProperties(BaseModel):
    content: str


class HeyGenVariable(BaseModel):
    name: str
    type: str = "text"
    properties: HeyGenVariableProperties


class HeyGenPayload(BaseModel):
    test: bool = True
    caption: bool = False
    title: str
    variables: Dict[str, HeyGenVariable]


class VideoDimension(BaseModel):
    width: int
    height: int


# Create a dimensions enum. 1080 and 720 are the only supported dimensions. Need both lenght and width.
class VideoDimensions(str, Enum):
    HD = "1080p"
    SD = "720p"
