# src/schema/video.py
from datetime import datetime
from uuid import UUID
from typing import Dict, Optional
from pydantic import BaseModel


class DeploymentPackageExtBase(BaseModel):
    deployment_package_id: int
    prompt_template: str


class DeploymentPackageExtCreate(DeploymentPackageExtBase):
    pass


class DeploymentPackageExtResponse(DeploymentPackageExtBase):
    id: UUID
    created_on: datetime
    updated_on: datetime

    class Config:
        from_attributes = True


class ScriptBase(BaseModel):
    student_deployment_id: int
    prompt_used: str


class ScriptCreate(ScriptBase):
    pass


class ScriptResponse(ScriptBase):
    id: UUID
    status: str
    content: Optional[str] = None
    scene_dialogue: Optional[Dict] = None
    variables: Optional[Dict] = None
    raw_llm_response: Optional[str] = None
    created_on: datetime
    updated_on: datetime

    class Config:
        from_attributes = True


class VideoBase(BaseModel):
    student_deployment_id: int
    script_id: UUID


class VideoCreate(VideoBase):
    pass


class VideoResponse(VideoBase):
    id: UUID
    status: str
    heygen_video_id: Optional[str] = None
    video_url: Optional[str] = None
    created_on: datetime
    updated_on: datetime

    class Config:
        from_attributes = True


class CreateVideoRequest(BaseModel):
    student_deployment_id: int
