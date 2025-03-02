# src/schema/video.py
from datetime import datetime, date
from uuid import UUID
from typing import Dict, List, Optional
from pydantic import BaseModel

from src.schema.base import BaseResponse

from tabulate import tabulate


# Base Models for API Responses
class TimeStampedModel(BaseModel):
    created_on: datetime
    updated_on: datetime


class DBModelBase(TimeStampedModel):
    id: UUID

    class Config:
        from_attributes = True


# Summary Models
class StepSummary(BaseModel):
    step_name: Optional[str] = None
    score: Optional[float] = None


class ComponentSummary(BaseModel):
    component_category: str
    score: Optional[float] = None
    steps: List[StepSummary] = []


# Grading Data Models
class DeploymentPackage(BaseModel):
    id: int
    name: str
    notes: Optional[str]
    objectives: Optional[str]


class DeploymentStep(StepSummary):
    grading: Optional[str] = None
    objectives: Optional[str] = None
    instructions: Optional[str] = None
    deployment_component_id: Optional[int] = None  # Links to component
    component_category: Optional[str] = None  # Category from dps


class DeploymentComponent(ComponentSummary):
    id: int
    description: Optional[str] = None
    grading: Optional[str] = None

    # Override steps to use DeploymentStep instead of StepSummary
    steps: List[DeploymentStep] = []

    @property
    def summary(self) -> ComponentSummary:
        """Return a simplified version with just the summary fields"""
        return ComponentSummary(
            component_category=self.component_category,
            score=self.score,
            steps=[
                StepSummary(step_name=step.step_name, score=step.score)
                for step in self.steps
            ],
        )


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
    components: List[DeploymentComponent] = []
    deployment_package: DeploymentPackage

    @property
    def components_summary(self) -> List[ComponentSummary]:
        return [component.summary for component in self.components]

    def get_simple_components_text(deployment_data):
        lines = []
        for comp in deployment_data.components_summary:
            score = comp.score if comp.score is not None else "N/A"
            lines.append(f"• {comp.component_category}: {score}")
        return "\n".join(lines)

    def get_simple_steps_text(deployment_data):
        lines = []
        for comp in deployment_data.components_summary:
            # lines.append(f"## {comp.component_category} (Score: {comp.score or 'N/A'})")
            for step in comp.steps:
                score = step.score if step.score is not None else "N/A"
                lines.append(f"  • {step.step_name}: {score}")
            lines.append("")
        return "\n".join(lines)

    def get_top_and_bottom_steps_text(self, top_n: int = 4, bottom_n: int = 4) -> str:
        """
        Get the top and bottom scored steps in a simple text format.

        Args:
            top_n (int): Number of top scores to include.
            bottom_n (int): Number of bottom scores to include.

        Returns:
            Formatted text with top and bottom steps.
        """
        # Extract all steps and their scores
        all_steps = []
        for comp in self.components_summary:
            for step in comp.steps:
                all_steps.append((step.step_name, step.score if step.score is not None else float('-inf')))

        # Sort steps by score (ascending order)
        sorted_steps = sorted(all_steps, key=lambda x: x[1], reverse=True)

        # Get top and bottom steps
        top_steps = sorted_steps[:top_n]
        bottom_steps = sorted_steps[-bottom_n:]

        # Format the results
        lines = []
        lines.append("High Scoring Steps:")
        for step_name, score in top_steps:
            lines.append(f"  • {step_name}: {score if score != float('-inf') else 'N/A'}")

        lines.append("Low Scoring Steps:")
        for step_name, score in bottom_steps:
            lines.append(f"  • {step_name}: {score if score != float('-inf') else 'N/A'}")

        return "\n".join(lines)


# API Models
class CreateVideoRequest(BaseModel):
    student_deployment_id: int


class VideoResponseData(DBModelBase):
    student_deployment_id: int
    script_id: UUID
    status: str
    heygen_video_id: Optional[str] = None
    video_url: Optional[str] = None

    class Config:
        from_attributes = True  # Enable ORM mode


class VideoResponse(BaseResponse[VideoResponseData]):
    pass
