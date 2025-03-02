# src/services/dialogue/video.py
import json

from typing import Any, Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from src.models.video import Script, Video
from src.api.dependencies.db import (
    select_student_deployment_details,
    get_student_info,
    get_cohort_scores,
    calculate_percentile_metrics,
)
from src.services.dialogue.script import generate as generate_script
from src.schema.video import StudentDeploymentDetails, VideoData
from src.settings import settings
from src.logging_config import app_logger


async def create(deployment_id: int, db: Session) -> VideoData:
    """
    Create a video for a deployment, handling script generation and HeyGen submission
    """
    # Check deployment exists and get data
    deployment_data: StudentDeploymentDetails = select_student_deployment_details(deployment_id)

    app_logger.debug("deployment data retrieved")

    if not deployment_data:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Get cohort comparison data
    # TODO: This needs to be done with pydantic models. Possibly added to select_student_deployment_details
    cohort_comparison = get_student_accuracy_percentile(deployment_id)

    app_logger.debug("Creating script")
    script: Script = await generate_script(
        deployment_data,
        cohort_comparison,
        db
    )

    # Create video record
    video: Video = Video(
        student_deployment_id=deployment_id,
        script_id=script.id,
        status="processing"
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    # Submit to HeyGen
    await submit_to_heygen(
        template_id=settings.HEYGEN_TEMPLATE_ID,
        student_data=deployment_data,
        script_data=script.scene_dialogue,
        percentile_data=cohort_comparison,
        api_key=settings.HEYGEN_API_KEY,
    )
    # TODO: This will need to return something else based on return of submit_to_heygen
    # Or maybe move this to another function
    return video


async def get(video_id: UUID, db: Session) -> Video:
    """Get video status"""
    return db.query(Video).filter(Video.id == video_id).first()


async def update_heygen_status(video_id: UUID, heygen_data: dict, db: Session):
    """
    Handle HeyGen webhook status updates
    """
    video = await get(video_id, db)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Update video with HeyGen status
    video.heygen_video_id = heygen_data.get('video_id')
    video.status = heygen_data.get('status')
    video.video_url = heygen_data.get('video_url')

    db.commit()
    db.refresh(video)
    return video


def get_student_accuracy_percentile(deployment_id: int) -> Dict:
    """
    Main function to get a student's accuracy percentile within their cohort.

    Args:
        deployment_id: The ID of the student's deployment

    Returns:
        Dict with student percentile information
    """
    # Get student info
    student_info = get_student_info(deployment_id)

    if not student_info:
        return {"error": f"No deployment found with ID {deployment_id}"}

    # Get cohort scores
    cohort_scores = get_cohort_scores(
        student_info.cohort_id, student_info.deployment_package_id
    )

    # Calculate metrics
    metrics = calculate_percentile_metrics(student_info.acc_score, cohort_scores)

    # Return combined result
    return {
        "student_name": f"{student_info.first_name} {student_info.last_name}",
        "cohort_name": student_info.cohort_name,
        "acc_score": student_info.acc_score,
        "cohort_avg_acc_score": metrics["cohort_avg_acc_score"],
        "percentile": metrics["percentile"],
        "rank": metrics["rank"],
    }


def build_heygen_payload(
    student_data: StudentDeploymentDetails,
    script_data: Dict[str, Dict[str, str]],
    percentile_data: Dict[str, Any],
    test_mode: bool = True,
) -> Dict[str, Any]:
    """
    Build the HeyGen API payload for video generation.

    Args:
        student_data: StudentDeploymentDetails with all student information
        script_data: Nested dictionary containing scene data
                    ({"1": {"scene_1_title": "...", "scene_1_script": "..."}})
        percentile_data: Dictionary with percentile information from get_student_accuracy_percentile
        template_id: HeyGen template ID to use
        test_mode: Whether to run in test mode (default: True)

    Returns:
        Dict with complete HeyGen API payload
    """
    # Format components and steps summary as text
    components_summary = student_data.get_simple_components_text()
    steps_summary = student_data.get_top_and_bottom_steps_text()

    # Set up all text variables
    variables = {
        # Student info
        "first_name": {
            "name": "first_name",
            "type": "text",
            "properties": {"content": student_data.first_name},
        },
        "last_name": {
            "name": "last_name",
            "type": "text",
            "properties": {"content": student_data.last_name},
        },
        "cohort_name": {
            "name": "cohort_name",
            "type": "text",
            "properties": {"content": student_data.cohort_name},
        },
        # Deployment info
        "deployment_package_name": {
            "name": "deployment_package_name",
            "type": "text",
            "properties": {"content": student_data.deployment_package.name},
        },
        "deployment_package_objectives": {
            "name": "deployment_package_objectives",
            "type": "text",
            "properties": {"content": student_data.deployment_package.objectives},
        },
        # Score info
        "acc_score": {
            "name": "acc_score",
            "type": "text",
            "properties": {
                "content": (
                    str(student_data.acc_score)
                    if student_data.acc_score is not None
                    else "N/A"
                )
            },
        },
        # Percentile comparison
        "cohort_percentile": {
            "name": "cohort_percentile",
            "type": "text",
            "properties": {"content": str(percentile_data.get("percentile", "N/A"))},
        },
        "cohort_avg_acc_score": {
            "name": "cohort_avg_acc_score",
            "type": "text",
            "properties": {
                "content": str(percentile_data.get("cohort_avg_acc_score", "N/A"))
            },
        },
        # Summaries
        "components_summary": {
            "name": "components_summary",
            "type": "text",
            "properties": {"content": components_summary},
        },
        "steps_summary": {
            "name": "steps_summary",
            "type": "text",
            "properties": {"content": steps_summary},
        },
    }

    # Extract and add all scene scripts and titles from the nested script_data
    for scene_number, scene_content in json.loads(script_data).items():
        for key, value in scene_content.items():
            if key.startswith("scene_") and (
                key.endswith("_script") or key.endswith("_title")
            ):
                variables[key] = {
                    "name": key,
                    "type": "text",
                    "properties": {"content": value},
                }

    # Create the complete payload
    payload = {
        "test": test_mode,
        "caption": False,
        "title": f"{student_data.first_name} {student_data.last_name} - {student_data.deployment_package.name} Feedback",
        "variables": variables,
    }

    app_logger.debug("HeyGen payload:")
    app_logger.debug(payload)

    return payload


async def submit_to_heygen(
    template_id: str,
    student_data: StudentDeploymentDetails,
    script_data: Dict,
    percentile_data: Dict,
    api_key: str,
) -> Dict[str, Any]:
    """Submit a video generation request to HeyGen with template validation."""
    import httpx

    # Build initial payload
    payload = build_heygen_payload(
        student_data=student_data,
        script_data=script_data,
        percentile_data=percentile_data,
    )

    # Fetch template info to get allowed variables
    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        # Get template info
        template_url = f"https://api.heygen.com/v2/template/{template_id}"
        template_response = await client.get(template_url, headers=headers)

        if not template_response.is_success:
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
            generate_url, headers=headers, json=filtered_payload
        )
        response_data = response.json()

        app_logger.debug("HeyGen response:")
        app_logger.debug(response_data)

        if (
            not response.is_success
            or "error" in response_data
            and response_data["error"]
        ):
            return {
                "success": False,
                "error": response_data.get("error", "Unknown error"),
                "status_code": response.status_code,
            }

        # Extract video ID from response
        video_id = response_data.get("data", {}).get("video_id")

        return {"success": True, "video_id": video_id, "response": response_data}


def filter_heygen_variables(template_info, payload):
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
    for var_name, var_data in payload["variables"].items():
        if var_name in allowed_variables:
            filtered_variables[var_name] = var_data
        else:
            print(f"Removing invalid variable: {var_name}")

    # Update payload with filtered variables
    filtered_payload = payload.copy()
    filtered_payload["variables"] = filtered_variables

    return filtered_payload
