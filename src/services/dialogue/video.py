# src/services/dialogue/video.py
import json
import uuid

from typing import Any, Dict, Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from src.models.video import Script, Video
from src.api.dependencies.db import (
    select_student_deployment_details,
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
    HeyGenResponseData,
    HeyGenVariableProperties,
    VideoData,
    VideoDimension,
    VideoStatus,
)
from src.models.video import DeploymentPackageExt, HeyGenTemplate
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

    # Submit to HeyGen
    # return details from HeyGen API response
    heygen_response: HeyGenResponseData = await submit_to_heygen(
        template_id=settings.HEYGEN_TEMPLATE_ID,
        script_prompt_data=script_prompt_data,
        script=script,
        db=db,
    )

    video.status = (
        VideoStatus.PROCESSING if heygen_response.success else VideoStatus.FAILED
    )
    video.heygen_video_id = heygen_response.video_id
    video.heygen_response = heygen_response
    db.commit()

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
    template_id: uuid.UUID,
    script_prompt_data: ScriptPromptData,
    script: Script,
    db: Session,
    options: Optional[Dict[str, Any]] = None,
) -> HeyGenResponseData:
    """
    Submit a video generation request to HeyGen

    Args:
        template_id: HeyGen template ID
        script_prompt_data: All data needed for script generation
        script: The generated script
        db: Database session
        options: Additional options for HeyGen API

    Returns:
        HeyGenResponseData with details about the submitted video
    """
    # Build payload using template-driven mapping with options
    payload: HeyGenPayload = await build_heygen_payload(
        template_id=template_id,
        script_prompt_data=script_prompt_data,
        script=script,
        db=db,
        options=options,
    )

    # Set up API request
    headers = {"X-Api-Key": settings.HEYGEN_API_KEY, "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        # Get template info
        template_url = f"https://api.heygen.com/v2/template/{template_id}"
        template_response = await client.get(template_url, headers=headers)

        if not template_response.is_success:
            app_logger.error(
                f"Failed to fetch template: {template_response.status_code}"
            )
            return HeyGenResponseData(
                success=False,
                error="Failed to fetch template information",
                status=VideoStatus.FAILED,
            )

        template_info = template_response.json()

        # Filter payload to only include valid variables
        filtered_payload: HeyGenPayload = filter_heygen_variables(
            template_info,
            payload
        )

        # Submit request
        generate_url = f"https://api.heygen.com/v2/template/{template_id}/generate"
        response = await client.post(
            generate_url, headers=headers, json=filtered_payload.dict()
        )

        response_data = response.json()

        if not response.is_success or (
            "error" in response_data and response_data["error"]
        ):
            error_msg = response_data.get("error", "Unknown error")
            app_logger.error(f"HeyGen API error: {error_msg}")
            return HeyGenResponseData(
                success=False, error=error_msg, status=VideoStatus.FAILED
            )

        # Process successful response
        heygen_video_id = response_data.get("data", {}).get("video_id")

        return HeyGenResponseData(
            success=True,
            video_id=heygen_video_id,
            status=VideoStatus.PROCESSING,
            response=response_data,
        )


async def build_heygen_payload(
    template_id: uuid.UUID,
    script_prompt_data: ScriptPromptData,
    script: Script,
    db: Session,
    options: Optional[Dict[str, Any]] = None,
) -> HeyGenPayload:
    """
    Build HeyGen payload using template-driven mapping

    Args:
        template_id: HeyGen template ID
        script_prompt_data: All data needed for script generation
        script: The generated script
        db: Database session
        options: Additional options for HeyGen API (dimension, include_gif, etc.)

    Returns:
        Complete HeyGen payload with all parameters
    """
    # Default options
    # If settings.environment set Dimension to 720p
    # TODO: Move to an Enum
    if settings.ENVIRONMENT == "production":
        options = options or {"dimension": {"width": 1920, "height": 1080}}
    else:
        options = options or {"dimension": {"width": 1920, "height": 720}}

    # Get template from database
    template = db.query(
        HeyGenTemplate
    ).filter_by(
        template_id=template_id
    ).first()
    if not template:
        raise ValueError(f"Template {template_id} not found")

    # Build context dynamically based on mappings
    required_models = get_required_models(
        template.variable_mappings.get("mappings", [])
    )

    app_logger.debug(f"Required models for HeyGen payload: {required_models}")

    # Initialize context builder
    context_builder = ContextBuilder(script_prompt_data, script)

    # Register models based on what's needed in the mappings
    if "student" in required_models:
        context_builder.register_model(
            "student", script_prompt_data.deployment_details.student
        )

    if "cohort" in required_models:
        context_builder.register_model(
            "cohort", script_prompt_data.deployment_details.cohort
        )

    if "deployment" in required_models:
        context_builder.register_model(
            "deployment", script_prompt_data.deployment_details.deployment
        )

    if "package" in required_models:
        context_builder.register_model(
            "package", script_prompt_data.deployment_details.package
        )

    if "cohort_comparison" in required_models:
        context_builder.register_model(
            "cohort_comparison",
            script_prompt_data.cohort_comparison,
            # Use empty dict if None
            dict_method="dict" if script_prompt_data.cohort_comparison else None,
        )

    if "script" in required_models:
        context_builder.register_script_data()

    # Get the built context
    mapping_context = context_builder.get_context()

    # Process mappings into variables
    variables = {}
    for mapping in template.variable_mappings.get("mappings", []):
        variable_name = mapping["variable_name"]
        value = extract_variable_value(mapping, mapping_context)

        if value is not None:
            variables[variable_name] = HeyGenVariable(
                name=variable_name,
                properties=HeyGenVariableProperties(content=str(value)),
            )

    # Create payload with base parameters
    payload_data = {
        "test": options.get("test", True),
        "caption": options.get("caption", False),
        "title": options.get(
            "title",
            f"{script_prompt_data.deployment_details.student.full_name} - {script_prompt_data.deployment_details.package.name} Feedback",
        ),
        "variables": variables,
        "include_gif": options.get("include_gif", False),
        "enable_sharing": options.get("enable_sharing", False),
    }

    # Add optional parameters if provided
    if "callback_id" in options:
        payload_data["callback_id"] = options["callback_id"]

    if "folder_id" in options:
        payload_data["folder_id"] = options["folder_id"]

    if "brand_voice_id" in options:
        payload_data["brand_voice_id"] = options["brand_voice_id"]

    # Handle dimension if provided
    if "dimension" in options:
        payload_data["dimension"] = VideoDimension(**options["dimension"])

    return HeyGenPayload(**payload_data)


def get_required_models(mappings: List[Dict]) -> set[str]:
    """
    Extract the set of required source models from mappings

    Args:
        mappings: List of mapping dictionaries

    Returns:
        Set of required source_model names
    """
    return {
        mapping["source_model"] for mapping in mappings if "source_model" in mapping
    }


def extract_variable_value(mapping: Dict, context: Dict) -> Any:
    """
    Extract and transform value based on variable mapping

    Args:
        mapping: The variable mapping configuration
        context: The data context with all source models

    Returns:
        Extracted and transformed value, or None if not found
    """
    source_model = mapping["source_model"]
    source_field = mapping["source_field"]
    transform_type = mapping.get("transformation_type", "none")
    transform_config = mapping.get("transformation_config", {})

    # Handle special method calls
    if source_model == "special":
        return handle_special_mapping(
            source_field, transform_type, transform_config, context
        )

    # Get the base model data
    if source_model not in context:
        return None
    model_data = context[source_model]

    # Extract the value based on transformation type
    if transform_type == "dict_access":
        value = get_nested_dict_value(
            model_data, source_field, transform_config.get("default_value")
        )
    else:
        # For simple field access, split by dots and traverse
        value = get_nested_dict_value(model_data, source_field)

    # Apply transformations
    return transform_value(value, transform_type, transform_config)


def handle_special_mapping(
    field: str, transform_type: str, config: Dict, context: Dict
) -> Any:
    """
    Handle special mappings like method calls

    Args:
        field: The field or method name
        transform_type: Type of transformation
        config: Configuration for the transformation
        context: Data context

    Returns:
        Result of the special mapping
    """
    if transform_type == "method_call":
        object_name = config.get("object")
        if not object_name or object_name not in context["special"]:
            return None

        obj = context["special"][object_name]
        method = getattr(obj, field, None)

        if not callable(method):
            return None

        args = config.get("args", [])
        kwargs = config.get("kwargs", {})
        return method(*args, **kwargs)

    return None


def get_nested_dict_value(data: Dict, path: str, default=None) -> Any:
    """
    Access nested dictionary values with dot notation path

    Args:
        data: Dictionary to access
        path: Dot-separated path to the value (e.g. "user.profile.name")
        default: Default value if path not found

    Returns:
        Value at the path or default if not found
    """
    parts = path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default

    return current


def transform_value(value: Any, transform_type: str, config: Dict) -> Any:
    """
    Apply transformations to a value

    Args:
        value: The value to transform
        transform_type: Type of transformation
        config: Configuration for the transformation

    Returns:
        Transformed value
    """
    if value is None:
        return config.get("default_value") if config else None

    if transform_type == "none":
        return value

    elif transform_type == "format_number":
        try:
            format_str = config.get("format", "{:.1f}")
            return format_str.format(value)
        except (ValueError, TypeError):
            return config.get("default_value", "N/A")

    elif transform_type == "default_if_null":
        return value if value is not None else config.get("default_value")

    elif transform_type == "string_format":
        try:
            format_str = config.get("format", "{}")
            return format_str.format(value)
        except (ValueError, TypeError):
            return config.get("default_value", "")

    # Add more transformations as needed

    return value


def filter_heygen_variables(template_info, payload: HeyGenPayload) -> HeyGenPayload:
    """
    Filter payload variables to only include those defined in the HeyGen template

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

    # Create new payload with filtered variables but keep all other fields
    payload_dict = payload.dict()
    payload_dict["variables"] = filtered_variables

    return HeyGenPayload(**payload_dict)


class ContextBuilder:
    """
    Dynamically builds a context for template variable mapping
    """

    def __init__(self, script_prompt_data, script):
        self.script_prompt_data = script_prompt_data
        self.script = script
        self._context = {}
        self._register_special_handlers()

    def _register_special_handlers(self):
        """Register special object handlers for method calls"""
        self._context["special"] = {"script_prompt_data": self.script_prompt_data}

    def register_model(self, name: str, model_obj, dict_method: str = "dict"):
        """
        Register a model in the context

        Args:
            name: The key to use in the context
            model_obj: The model object
            dict_method: Method name to convert object to dict (default: "dict")
        """
        if model_obj is None:
            self._context[name] = {}
            return

        if hasattr(model_obj, dict_method) and callable(
            getattr(model_obj, dict_method)
        ):
            self._context[name] = getattr(model_obj, dict_method)()
        elif isinstance(model_obj, dict):
            self._context[name] = model_obj
        else:
            # Fall back to __dict__ if no dict method available
            self._context[name] = model_obj.__dict__

    def register_script_data(self):
        # TODO: Needs a pydantic model for scene_dialogue
        """Register script data with special handling for scene_dialogue"""
        script_data = {
            "scene_dialogue": (
                json.loads(self.script.scene_dialogue)
                if isinstance(self.script.scene_dialogue, str)
                else self.script.scene_dialogue
            )
        }
        self._context["script"] = script_data

    def get_context(self):
        """Get the built context dictionary"""
        return self._context


# TO DO: This could be the PATCH or UPDATE route.
async def submit_to_heygen_by_deployment_id(
    student_deployment_id: int,
    db: Session,
) -> VideoData:
    """
    Submit a video to HeyGen using existing script and video details for a given student_deployment_id.
    Skips script and video generation.
    """
    # Fetch the existing video record
    video: Optional[Video] = (
        db.query(Video)
        .filter(Video.student_deployment_id == student_deployment_id)
        .first()
    )
    if not video:
        raise HTTPException(
            status_code=404, detail="Video not found for the given deployment ID"
        )

    # Fetch the associated script
    script: Optional[Script] = (
        db.query(Script).filter(Script.id == video.script_id).first()
    )
    if not script:
        raise HTTPException(status_code=404, detail="Script not found for the video")

    # Fetch script prompt data (if needed for HeyGen submission)
    script_prompt_data: ScriptPromptData = get_script_prompt_data(
        student_deployment_id, db
    )

    # Submit to HeyGen
    heygen_response: HeyGenResponseData = await submit_to_heygen(
        template_id=settings.HEYGEN_TEMPLATE_ID,
        script_prompt_data=script_prompt_data,
        script=script,
        db=db,
    )

    # Update video status and HeyGen details
    video.status = (
        VideoStatus.PROCESSING if heygen_response.success else VideoStatus.FAILED
    )
    video.heygen_video_id = heygen_response.video_id
    video.heygen_response = heygen_response
    db.commit()
    db.refresh(video)

    return VideoData.from_orm(video)
