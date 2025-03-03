# src/services/dialogue/video.py
import json
from typing import Any, Dict, Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from src.models.video import Script, Video
from src.api.dependencies.db import (
    select_student_deployment_details,
    select_cohort,
    select_cohort_scores,
)
from src.services.dialogue.script import generate as generate_script
from src.schema.itp import (
    CohortComparison,
    ScriptPromptData,
    StudentDeploymentDetails,
)
from src.schema.video import (
    HeyGenVariable,
    HeyGenPayload,
    HeyGenVariableProperties,
    VideoData,
    VideoStatus,
)
from src.models.video import DeploymentPackageExt
from src.settings import settings
from src.logging_config import app_logger

import httpx


async def create(student_deployment_id: int, db: Session) -> VideoData:
    """
    Create a video for a deployment, handling script generation and HeyGen submission
    """

    script_prompt_data: ScriptPromptData = get_script_prompt_data(
        student_deployment_id,
        db
    )

    app_logger.debug("Script prompt data retrieved")

    # Generate script
    app_logger.debug("Creating script")
    script: Script = await generate_script(
        script_prompt_data,
        db
    )

    # Create video record
    video: Video = Video(
        student_deployment_id=script_prompt_data.deployment_details.deployment.id,
        script_id=script.id,
        status=VideoStatus.NOT_SUBMITTED,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    breakpoint()

    # Submit to HeyGen
    # return details from HeyGen API response
    await submit_to_heygen(
        template_id=settings.HEYGEN_TEMPLATE_ID,
        student_deployment_data=script_prompt_data.deployment_details.deployment,
        script_data=script.scene_dialogue,
        cohort_data=script_prompt_data.deployment_details.cohort_comparison,
        api_key=settings.HEYGEN_API_KEY,
        video_id=video.id,
    )

    return VideoData.from_orm(video)


def get_script_prompt_data(
    student_deployment_id: int,
    db: Session,
) -> Optional[ScriptPromptData]:
    """
    Get complete data needed for script generation.
    Uses query chaining where possible for efficiency.

    Args:
        student_deployment_id: The ID of the student deployment
        include_cohort_comparison: Whether to include cohort comparison data

    Returns:
        ScriptPromptData model or None if not found
    """
    # Get complete deployment details
    student_deployment_details: StudentDeploymentDetails = select_student_deployment_details(
        student_deployment_id
    )
    if not student_deployment_details:
        return None

    # Get cohort comparison if requested
    cohort_comparison = None
    if (
        student_deployment_details.deployment.acc_score is not None
    ):
        # Get cohort scores
        cohort_scores = select_cohort_scores(
            cohort_id=student_deployment_details.cohort.id,
            package_id=student_deployment_details.deployment.package_id
        )

        # Calculate comparison metrics
        cohort_comparison = calculate_cohort_comparison(
            student_deployment_details.deployment.acc_score, cohort_scores
        )

    components_summary = [
        {
            "component_category": component.component_category,
            "score": component.score,
            "steps": [
                {"step_name": step.step_name, "score": step.score}
                for step in component.steps
            ],
        }
        for component in student_deployment_details.deployment.components
    ]

    stmt = select(DeploymentPackageExt).where(
        DeploymentPackageExt.deployment_package_id == student_deployment_details.deployment.package_id
    )
    deployment_package: DeploymentPackageExt = db.execute(stmt).scalar_one()

    student_deployment_details.package.prompt = deployment_package.prompt_template

    # Create comprehensive data model
    return ScriptPromptData(
        deployment_details=student_deployment_details,
        cohort_comparison=cohort_comparison,
        components_summary=components_summary
    )


def _get_ordinal_suffix(n: int) -> str:
    """Return the ordinal suffix for a number."""
    if 11 <= n % 100 <= 13:
        return "th"
    else:
        return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def calculate_cohort_comparison(
    student_score: float, cohort_scores: List[float]
) -> CohortComparison:
    """
    Calculate percentile and related metrics for a student within their cohort.

    Args:
        student_score: The student's accuracy score
        cohort_scores: List of accuracy scores for the cohort

    Returns:
        CohortComparison object with calculated metrics
    """
    total_students = len(cohort_scores)

    if total_students == 0:
        return CohortComparison(
            total_students=0,
            students_below_or_equal=0,
            cohort_avg_acc_score=0.0,
            percentile=0.0,
            rank="N/A",
        )

    # Count students with score <= student_score
    students_below_or_equal = sum(
        1 for score in cohort_scores if score <= student_score
    )

    # Calculate average score
    cohort_avg_acc_score = sum(cohort_scores) / total_students

    # Calculate percentile
    percentile = (students_below_or_equal / total_students) * 100

    # Get rank ordinal
    rank_ordinal = _get_ordinal_suffix(students_below_or_equal)
    rank = f"{students_below_or_equal}{rank_ordinal} out of {total_students}"

    return CohortComparison(
        total_students=total_students,
        students_below_or_equal=students_below_or_equal,
        cohort_avg_acc_score=round(cohort_avg_acc_score, 2),
        percentile=round(percentile, 1),
        rank=rank,
    )


async def submit_to_heygen(
    template_id: str,
    student_deployment_details: StudentDeploymentDetails,
    script_data: Dict,
    cohort_data: CohortComparison,
) -> Dict[str, Any]:
    """Submit a video generation request to HeyGen with template validation."""

    # Build initial payload
    payload = build_heygen_payload(
        student_data=student_data,
        script_data=script_data,
        cohort_data=cohort_data,
    )

    headers = {
        "X-Api-Key": settings.HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        # Get template info
        template_url = f"https://api.heygen.com/v2/template/{template_id}"
        template_response = await client.get(template_url, headers=headers)

        if not template_response.is_success:
            app_logger.error(
                f"Failed to fetch template: {template_response.status_code}"
            )
            return {
                "success": False,
                "error": "Failed to fetch template information",
                "status_code": template_response.status_code,
            }

        template_info = template_response.json()

        # Filter payload to only include valid variables
        filtered_payload = filter_heygen_variables(template_info, payload)

        # Now make the generate request with valid variables
        generate_url = f"https://api.heygen.com/v2/template/{template_id}/generate"
        response = await client.post(
            generate_url, headers=headers, json=filtered_payload.dict()
        )
        response_data = response.json()

        app_logger.debug("HeyGen response received")

        if (
            not response.is_success
            or "error" in response_data
            and response_data["error"]
        ):
            app_logger.error(
                f"HeyGen API error: {response_data.get('error', 'Unknown error')}"
            )
            return {
                "success": False,
                "error": response_data.get("error", "Unknown error"),
                "status_code": response.status_code,
            }

        # Extract video ID from response
        heygen_video_id = response_data.get("data", {}).get("video_id")

        return {
            "success": True,
            "video_id": heygen_video_id,
            "response": response_data,
        }
