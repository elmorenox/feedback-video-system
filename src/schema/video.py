# src/schema/video.py
from datetime import datetime, date
from uuid import UUID
from typing import Dict, List, Optional
from pydantic import BaseModel


# Base Models for API Responses
class TimeStampedModel(BaseModel):
    created_on: datetime
    updated_on: datetime


class DBModelBase(TimeStampedModel):
    id: UUID

    class Config:
        from_attributes = True


# Grading Data Models
class DeploymentPackage(BaseModel):
    id: int
    name: str
    description: str


class DeploymentStep(BaseModel):
    grading: Optional[str] = None
    score: Optional[float] = None
    objectives: Optional[str] = None
    instructions: Optional[str] = None


class DeploymentComponent(BaseModel):
    grading: Optional[str] = None
    score: Optional[float] = None
    deployment_component_id: Optional[int] = None


class StudentDeploymentDetails(BaseModel):
    # Student Info
    first_name: str
    last_name: str
    email: str
    tech_experience_id: int
    employment_status_id: int

    # Cohort Info
    cohort_name: str
    cohort_start_date: date
    cohort_end_date: date

    # Deployment Info
    deployment_id: int
    deployment_start_date: date
    deployment_end_date: date

    # Grading Info
    acc_grading: Optional[str] = None
    acc_score: Optional[float] = None
    otd_grading: Optional[str] = None
    otd_score: Optional[float] = None
    opt_grading: Optional[str] = None
    opt_score: Optional[float] = None
    func_grading: Optional[str] = None
    func_score: Optional[float] = None

    # Related Data
    steps: List[DeploymentStep]
    components: List[DeploymentComponent]
    deployment_package: DeploymentPackage


# API Models
class CreateVideoRequest(BaseModel):
    student_deployment_id: int


class VideoResponse(DBModelBase):
    student_deployment_id: int
    script_id: UUID
    status: str
    heygen_video_id: Optional[str] = None
    video_url: Optional[str] = None


class ScriptResponse(DBModelBase):
    student_deployment_id: int
    prompt_used: str
    status: str
    content: Optional[str] = None
    scene_dialogue: Optional[Dict] = None
    variables: Optional[Dict] = None
    raw_llm_response: Optional[str] = None
