# src/services/dialogue/video.py
import uuid

from typing import Any, Dict, Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from src.models.video import (
    DeploymentPackageExt,
    HeyGenTemplate,
    Script as ORMScript,
    Video,
)
from src.api.dependencies.db import (
    select_student_deployment,
    select_cohort_scores,
)
from src.services.dialogue.script import generate as generate_script
from src.schema.itp import (
    CohortComparison,
    StudentDeployment,
    StudentStepSummary,
    StudentComponentSummary,
)
from src.schema.video import (
    HeyGenVariable,
    HeyGenPayload,
    HeyGenResponseData,
    HeyGenVariableProperties,
    HeyGenWebhookEvent,
    Script,
    ScriptRequestPayload,
    VideoData,
    VideoDimension,
    VideoStatus,
)
from src.settings import settings
from src.logging_config import app_logger

import httpx

HEYGEN_HEADERS = {
    "accept": "application/json",
    "x-api-key": settings.HEYGEN_API_KEY
}


async def create(student_deployment_id: int, db: Session) -> VideoData:
    """
    POST Endpoint implementation: Create a video for a deployment,
    Create a video for a deployment,
    handling script generation and HeyGen submission.
    Returns existing video if one already exists for the deployment.
    """
    # Check if video already exists for this deployment
    existing_video = (
        db.query(Video)
        .filter(Video.student_deployment_id == student_deployment_id)
        .first()
    )

    if existing_video:
        return VideoData.model_validate(existing_video)

    # Always create a new script for POST requests
    script_request_payload = get_script_request_payload(
        student_deployment_id,
        db
    )

    script = await generate_script(script_request_payload, db)

    # Create video record
    video = Video(
        student_deployment_id=student_deployment_id,
        script_id=script.id,
        status=VideoStatus.NOT_SUBMITTED,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    # Submit to HeyGen
    heygen_response = await submit_to_heygen(
        template_id=settings.HEYGEN_TEMPLATE_ID,
        script_request_payload=script_request_payload,
        script=script,
        db=db,
    )

    video.status = (
        VideoStatus.PROCESSING if heygen_response.success else VideoStatus.FAILED
    )
    video.heygen_video_id = heygen_response.video_id
    video.heygen_response = heygen_response
    db.commit()

    return VideoData.model_validate(video)


def get_script_request_payload(
    student_deployment_id: int,
    db: Session,
) -> Optional[ScriptRequestPayload]:
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
    student_deployment: StudentDeployment = select_student_deployment(
        student_deployment_id
    )
    if not student_deployment:
        return None

    cohort_comparison = None
    if (
        student_deployment.acc_score is not None
    ):
        # Get cohort scores
        cohort_scores = select_cohort_scores(
            cohort_id=student_deployment.cohort.id,
            package_id=student_deployment.deployment_package.id
        )

        # Calculate comparison metrics
        cohort_comparison: CohortComparison = calculate_cohort_comparison(
            student_deployment.acc_score, cohort_scores
        )

    # construct components summary List[StudentComponentSummary]
    # use components. construct StudentStepSummary and StudentComponentSummary

    components_summary: List[StudentComponentSummary] = [
        StudentComponentSummary(
            component_category=comp.component_category,
            score=comp.score,
            steps=[
                StudentStepSummary(
                    step_name=step.step_name,
                    score=step.score
                )
                for step in comp.steps
            ]
        )
        for comp in student_deployment.components
    ]

    student_deployment.components_summary = components_summary

    stmt = select(DeploymentPackageExt).where(
        DeploymentPackageExt.deployment_package_id
        == student_deployment.deployment_package.id
    )

    deployment_package: DeploymentPackageExt = db.execute(stmt).scalar_one()

    return ScriptRequestPayload(
        prompt=deployment_package.prompt_template,
        student_deployment=student_deployment,
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


async def submit_to_heygen(
    template_id: uuid.UUID,
    script_request_payload: ScriptRequestPayload,
    script: ORMScript,
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
        student_deployment=script_request_payload.student_deployment,
        cohort_comparison=script_request_payload.cohort_comparison,
        script=script,
        db=db,
        options=options,
    )

    async with httpx.AsyncClient() as client:
        # Get template info
        template_url = f"https://api.heygen.com/v2/template/{template_id}"
        template_response = await client.get(
            template_url,
            headers=HEYGEN_HEADERS
        )

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
            generate_url,
            headers=HEYGEN_HEADERS,
            json=filtered_payload.model_dump()
        )

        response_data = response.json()

        if not response.is_success:
            # Extract error message with fallbacks for different error formats
            error_msg = "Unknown error"

            # Check for error in the "error" object structure
            if isinstance(response_data.get("error"), dict):
                error_msg = response_data["error"].get("message", error_msg)

            # Check for code/message direct structure
            elif "message" in response_data:
                error_msg = response_data.get("message", error_msg)
            app_logger.error(f"HeyGen API error: {error_msg}")
            return HeyGenResponseData(
                success=False, error=error_msg, status=VideoStatus.FAILED
            )

        # Process successful response
        heygen_video_id: str = response_data.get("data", {}).get("video_id")

        return HeyGenResponseData(
            success=True,
            video_id=heygen_video_id,
            status=VideoStatus.PROCESSING,
            response=response_data,
        )


async def build_heygen_payload(
    template_id: uuid.UUID,
    student_deployment: StudentDeployment,
    cohort_comparison: Optional[CohortComparison],
    script: ORMScript,
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
        options: Additional options
        for HeyGen API (dimension, include_gif, etc.)

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

    # Initialize context builder
    context_builder = ContextBuilder(student_deployment, script)

    # Register models based on what's needed in the mappings
    if "student" in required_models:
        context_builder.register_model(
            "student", student_deployment.student
        )

    if "cohort" in required_models:
        context_builder.register_model(
            "cohort", student_deployment.cohort
        )

    if "student_deployment" in required_models:
        context_builder.register_model(
            "student_deployment", student_deployment
        )

    if "deployment_package" in required_models:
        context_builder.register_model(
            "deployment_package", student_deployment.deployment_package
        )

    if "cohort_comparison" in required_models:
        context_builder.register_model(
            "cohort_comparison",
            cohort_comparison,
            # Use empty dict if None
            dict_method="dict" if cohort_comparison else None,
        )

    if "script" in required_models:
        context_builder.register_model(
            "script",
            script,
            dict_method="dict"
        )

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
            f"{student_deployment.student.full_name} - {student_deployment.deployment_package.name} Feedback",
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
        mapping["source_model"]
        for mapping in mappings
        if "source_model" in mapping
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


def filter_heygen_variables(
        template_info, payload: HeyGenPayload
) -> HeyGenPayload:
    """
    Filter payload variables to only include those defined in the HeyGen template

    Args:
        template_info: Response from HeyGen template GET request
        payload: Original payload with all variables

    Returns:
        Updated payload with only valid variables
    """
    # Extract allowed variable names from template info
    allowed_variables = set(
        template_info.get(
            "data", {}
            ).get(
                "variables", {}
                ).keys()
            )

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

    def __init__(self, student_deployment, script):
        self.student_deployment = student_deployment
        self.script = script
        self._context = {}
        self._register_special_handlers()

    def _register_special_handlers(self):
        """Register special object handlers for method calls"""
        self._context["special"] = {
            "student_deployment":
            self.student_deployment
        }

    def register_model(self, name: str, model_obj, dict_method: str = "dict"):
        """
        Register a model in the context

        Args:
            name: The key to use in the context
            model_obj: The model object
            dict_method: Method name
            to convert object to dict (default: "dict")
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

    def get_context(self):
        """Get the built context dictionary"""
        return self._context


async def update_video(
        student_deployment_id: int,
        db: Session
) -> VideoData:
    """
    PUT endpoint implementation: Complete replacement of a video resource.
    Generates a new script and video, deletes the old video from HeyGen.

    Args:
        student_deployment_id: The ID of the student deployment
        db: Database session

    Returns:
        Updated Video object
    """
    # Check if video exists
    existing_video = (
        db.query(Video)
        .filter(Video.student_deployment_id == student_deployment_id)
        .first()
    )

    # If video exists, delete it from HeyGen
    if existing_video:
        if existing_video.heygen_video_id:
            await delete_heygen_video(existing_video.heygen_video_id)

        # Mark old video as deleted in database
        existing_video.status = VideoStatus.REGENERATING
        db.commit()
    else:
        raise HTTPException(
            status_code=404,
            detail="Video not found for the given deployment ID"
        )

    # Generate completely new script and video (similar to create function)
    script_request_payload: ScriptRequestPayload = get_script_request_payload(
        student_deployment_id, db
    )

    app_logger.debug("Script prompt data retrieved for update")

    # Generate new script
    app_logger.debug("Creating new script for update")

    script: ORMScript = await generate_script(script_request_payload, db)

    # Update existing record
    video = existing_video
    video.script_id = script.id
    video.status = VideoStatus.NOT_SUBMITTED
    video.heygen_video_id = None
    video.heygen_response = None
    video.video_url = None

    db.commit()
    db.refresh(video)

    # Submit to HeyGen
    heygen_response: HeyGenResponseData = await submit_to_heygen(
        template_id=settings.HEYGEN_TEMPLATE_ID,
        script_request_payload=script_request_payload,
        script=script,
        db=db,
    )

    video.status = (
        VideoStatus.PROCESSING
        if heygen_response.success
        else VideoStatus.FAILED
    )
    video.heygen_video_id = heygen_response.video_id
    video.heygen_response = heygen_response
    db.commit()

    return video


async def patch_video(
    student_deployment_id: int, reuse_script: bool = True, db: Session = None
) -> VideoData:
    """
    PATCH endpoint implementation: Partial update of a video resource.
    By default reuses existing script and only regenerates the video.

    Args:
        student_deployment_id: The ID of the student deployment
        reuse_script: Whether to reuse the existing script (default: True)
        db: Database session

    Returns:
        Updated VideoData object
    """
    # Check if video exists
    existing_video: Video = (
        db.query(Video)
        .filter(Video.student_deployment_id == student_deployment_id)
        .first()
    )

    if not existing_video:
        raise HTTPException(
            status_code=404, detail="Video not found for the given deployment ID"
        )

    # If video exists, delete it from HeyGen
    if existing_video.heygen_video_id:
        await delete_heygen_video(existing_video.heygen_video_id)

    # Mark as regenerating to indicate the transition state
    existing_video.status = VideoStatus.REGENERATING
    db.commit()

    script_request_payload: ScriptRequestPayload = get_script_request_payload(
        student_deployment_id,
        db
    )

    # Either reuse existing script or generate a new one
    if reuse_script and existing_video.script_id:
        # Fetch the existing script
        orm_script: ORMScript = (
            db.query(ORMScript)
            .filter(ORMScript.id == existing_video.script_id)
            .first()
        )

        script = Script.model_validate(orm_script)

        if not orm_script:
            app_logger.warning(
                f"Script {existing_video.script_id} not found, generating new script"
            )
            script: Script = await generate_script(script_request_payload, db)
    else:
        # Generate a new script
        script: Script = await generate_script(script_request_payload, db)
        existing_video.script_id = script.id

    # Reset video properties for new submission
    existing_video.status = VideoStatus.NOT_SUBMITTED
    existing_video.heygen_video_id = None
    existing_video.video_url = None
    db.commit()

    # Submit to HeyGen
    heygen_response: HeyGenResponseData = await submit_to_heygen(
        template_id=settings.HEYGEN_TEMPLATE_ID,
        script_request_payload=script_request_payload,
        script=script,
        db=db,
    )

    # Update video with HeyGen response
    existing_video.status = (
        VideoStatus.PROCESSING
        if heygen_response.success
        else VideoStatus.FAILED
    )
    existing_video.heygen_video_id = heygen_response.video_id
    existing_video.heygen_response = heygen_response
    db.commit()

    return VideoData.model_validate(existing_video)


async def delete_heygen_video(video_id: str) -> bool:
    """
    Delete a video from HeyGen

    Args:
        video_id: HeyGen video ID

    Returns:
        bool: True if deletion was successful
    """
    if not video_id:
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://api.heygen.com/v1/video.delete?video_id={video_id}",
                headers=HEYGEN_HEADERS,
            )

        if response.status_code == 200:
            app_logger.info(
                f"Successfully deleted video {video_id} from HeyGen"
            )
            return True
        else:
            app_logger.error(
                f"""Failed to delete video {video_id} from HeyGen:
                {response.status_code}"""
            )
            return False
    except Exception as e:
        app_logger.error(f"Error deleting video from HeyGen: {e}")
        return False


async def heygen_event_handler(
        event: HeyGenWebhookEvent,
        db: Session
) -> bool:
    """
    Process HeyGen webhook events
    Updates the video status based on the event type

    Args:
        event: The webhook event from HeyGen

    Returns:
        bool: True if the event was processed successfully
    """
    event_type = event.event_type
    heygen_video_id = event.event_data.video_id

    try:
        # Find the video by heygen_video_id
        video = (
            db.query(Video)
            .filter(Video.heygen_video_id == heygen_video_id)
            .first()
        )

        if not video:
            app_logger.warning(
                f"Received webhook for unknown video: {heygen_video_id}"
            )
            return False

        if event_type == "avatar_video.success":
            # Update video status to completed and set the video URL
            video.status = VideoStatus.COMPLETED
            video.video_url = event.event_data.url

            # Store callback_id if provided
            if event.event_data.callback_id:
                video.callback_id = event.event_data.callback_id

        elif event_type == "avatar_video.fail":
            # Update video status to failed
            video.status = VideoStatus.FAILED

        else:
            app_logger.warning(f"Unhandled event type: {event_type}")
            return False

        # Commit changes to the database
        db.commit()

        app_logger.info(f"Processed {event_type} for video {heygen_video_id}")
        return True

    except Exception as e:
        app_logger.error(f"Error processing webhook: {e}")
        db.rollback()
        return False


async def delete_video(student_deployment_id: int, db: Session) -> bool:
    """
    DELETE endpoint implementation: Permanently removes a video and its associated script.
    Deletes the video from HeyGen if it exists there and removes database records.

    Args:
        student_deployment_id: The ID of the student deployment
        db: Database session

    Returns:
        bool: True if deletion was successful
    """
    # Find the video
    video = (
        db.query(Video)
        .filter(Video.student_deployment_id == student_deployment_id)
        .first()
    )

    if not video:
        raise HTTPException(
            status_code=404,
            detail="Video not found for the given deployment ID"
        )

    # Store script ID for later
    script_id = video.script_id

    # Delete from HeyGen if video ID exists
    if video.heygen_video_id:
        await delete_heygen_video(video.heygen_video_id)
        app_logger.info(f"Deleted video {video.heygen_video_id} from HeyGen")

    # Now delete the script if it exists
    if script_id:
        script = db.query(ORMScript).filter(ORMScript.id == script_id).first()
        if script:
            db.delete(script)
            db.commit()
            app_logger.info(f"Deleted script record with ID {script_id}")

    # Delete video from database
    db.delete(video)
    db.commit()
    app_logger.info(
        f"Deleted video record for deployment {student_deployment_id}"
    )

    return True
