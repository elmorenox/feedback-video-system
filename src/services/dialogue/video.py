# src/services/dialogue/video.py
import json
from typing import Any, Dict, Optional, List
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
    StudentDeploymentDetails
)
from src.schema.video import (
    HeyGenVariable,
    HeyGenPayload,
    HeyGenVariableProperties,
    VideoData
)
from src.settings import settings
from src.logging_config import app_logger

import httpx


async def create(student_deployment_id: int, db: Session) -> VideoData:
    """
    Create a video for a deployment, handling script generation and HeyGen submission
    """

    script_prompt_data: ScriptPromptData = get_script_prompt_data(
        student_deployment_id
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
        status="processing"
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
    student_deployment_id: int, include_cohort_comparison: bool = True
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
    # Get cohort information
    cohort = select_cohort(student_deployment_id=student_deployment_id)
    if not cohort:
        return None

    # Get complete deployment details
    student_deployment_details: StudentDeploymentDetails = select_student_deployment_details(
        student_deployment_id
    )
    if not student_deployment_details:
        return None

    # Get cohort comparison if requested
    cohort_comparison = None
    if (
        include_cohort_comparison
        and student_deployment_details.deployment.acc_score is not None
    ):
        # Get cohort scores
        cohort_scores = select_cohort_scores(
            cohort_id=cohort.id,
            package_id=student_deployment_details.deployment.package_id
        )

        # Calculate comparison metrics
        cohort_comparison = calculate_cohort_comparison(
            student_deployment_details.deployment.acc_score, cohort_scores
        )

    # Create comprehensive data model
    return ScriptPromptData(
        deployment_details=student_deployment_details,
        cohort_comparison=cohort_comparison,
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


def build_heygen_payload(
    student_data: StudentDeploymentDetails,
    script_data: Dict[str, Dict[str, str]],
    cohort_data: CohortComparison,
    test_mode: bool = True,
) -> HeyGenPayload:
    """
    Build the HeyGen API payload for video generation.

    Args:
        student_data: StudentDeployment with all student information
        script_data: Nested dictionary containing scene data
        cohort_data: CohortComparisonData with percentile information
        test_mode: Whether to run in test mode (default: True)

    Returns:
        HeyGenPayload object with complete API payload
    """
    # Format components and steps summary as text
    components_summary = student_data.get_simple_components_text()
    steps_summary = student_data.get_top_and_bottom_steps_text()

    # Create variables dictionary
    variables = {}

    # Add student info variables
    variables.update(_create_student_variables(student_data))

    # Add deployment info variables
    variables.update(_create_deployment_variables(student_data))

    # Add score info variables
    variables.update(_create_score_variables(student_data, cohort_data))

    # Add summary variables
    variables.update(
        {
            "components_summary": HeyGenVariable(
                name="components_summary",
                properties=HeyGenVariableProperties(content=components_summary),
            ),
            "steps_summary": HeyGenVariable(
                name="steps_summary",
                properties=HeyGenVariableProperties(content=steps_summary),
            ),
        }
    )

    # Add script variables
    variables.update(_create_script_variables(script_data))

    # Create the complete payload
    payload = HeyGenPayload(
        test=test_mode,
        caption=False,
        title=f"{student_data.first_name} {student_data.last_name} - {student_data.deployment_package.name} Feedback",
        variables=variables,
    )

    app_logger.debug("HeyGen payload created")

    return payload


def _create_student_variables(
    student_data: StudentDeploymentDetails,
) -> Dict[str, HeyGenVariable]:
    """Create HeyGen variables for student information"""
    return {
        "first_name": HeyGenVariable(
            name="first_name",
            properties=HeyGenVariableProperties(content=student_data.first_name),
        ),
        "last_name": HeyGenVariable(
            name="last_name",
            properties=HeyGenVariableProperties(content=student_data.last_name),
        ),
        "cohort_name": HeyGenVariable(
            name="cohort_name",
            properties=HeyGenVariableProperties(content=student_data.cohort_name),
        ),
    }


def _create_deployment_variables(
    student_data: StudentDeploymentDetails,
) -> Dict[str, HeyGenVariable]:
    """Create HeyGen variables for deployment information"""
    return {
        "deployment_package_name": HeyGenVariable(
            name="deployment_package_name",
            properties=HeyGenVariableProperties(
                content=student_data.deployment_package.name
            ),
        ),
        "deployment_package_objectives": HeyGenVariable(
            name="deployment_package_objectives",
            properties=HeyGenVariableProperties(
                content=student_data.deployment_package.objectives
                or "No objectives provided"
            ),
        ),
    }


def _create_score_variables(
    student_data: StudentDeploymentDetails, cohort_data: CohortComparison
) -> Dict[str, HeyGenVariable]:
    """Create HeyGen variables for score information"""
    return {
        "acc_score": HeyGenVariable(
            name="acc_score",
            properties=HeyGenVariableProperties(
                content=(
                    str(student_data.acc_score)
                    if student_data.acc_score is not None
                    else "N/A"
                )
            ),
        ),
        "cohort_percentile": HeyGenVariable(
            name="cohort_percentile",
            properties=HeyGenVariableProperties(
                content=cohort_data.formatted_percentile
            ),
        ),
        "cohort_avg_acc_score": HeyGenVariable(
            name="cohort_avg_acc_score",
            properties=HeyGenVariableProperties(
                content=str(cohort_data.cohort_avg_acc_score or "N/A")
            ),
        ),
    }


def _create_script_variables(script_data: Dict) -> Dict[str, HeyGenVariable]:
    """Create HeyGen variables from script data"""
    variables = {}

    # Extract and add all scene scripts and titles from the nested script_data
    for scene_number, scene_content in json.loads(script_data).items():
        for key, value in scene_content.items():
            if key.startswith("scene_") and (
                key.endswith("_script") or key.endswith("_title")
            ):
                variables[key] = HeyGenVariable(
                    name=key, properties=HeyGenVariableProperties(content=value)
                )

    return variables


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


def filter_heygen_variables(template_info, payload: HeyGenPayload) -> HeyGenPayload:
    """
    Filter payload variables to only include those defined in the HeyGen template.

    Args:
        template_info: Response from HeyGen template GET request
        payload: Original payload with all variables

    Returns:
        Updated payload with only valid variables
    """
    # Extract allowed variable names from template info
    allowed_variables = set(template_info.get("data", {}).get("variables", {}).keys())

    # Filter payload variables
    filtered_variables = {}
    for var_name, var_data in payload.variables.items():
        if var_name in allowed_variables:
            filtered_variables[var_name] = var_data
        else:
            app_logger.warning(f"Removing invalid variable: {var_name}")

    # Create new payload with filtered variables
    filtered_payload = HeyGenPayload(
        test=payload.test,
        caption=payload.caption,
        title=payload.title,
        variables=filtered_variables,
    )

    return filtered_payload
