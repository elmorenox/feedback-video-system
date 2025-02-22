# src/services/dialogue/video.py
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException

from src.models.video import Script, Video
from src.api.dependencies.db import select_student_deployment_details
from src.services.dialogue.script import generate as generate_script
from src.logging_config import app_logger


async def create(deployment_id: int, db: Session) -> Video:
    """
    Create a video for a deployment, handling script generation and HeyGen submission
    """
    # Check deployment exists and get data
    deployment_data = select_student_deployment_details(deployment_id)

    app_logger.debug("deployment data retrieved")

    if not deployment_data:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Check for existing video
    existing_video = db.query(Video).filter(
        Video.student_deployment_id == deployment_id
    ).first()
    if existing_video:
        return existing_video

    # Start transaction
    try:
        # Generate script
        app_logger.debug("Creating script")
        script = await generate_script(deployment_data, db)

        # Create video record
        video = Video(
            student_deployment_id=deployment_id,
            script_id=script.id,
            status="processing"
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        # Submit to HeyGen
        await submit_to_heygen(video.id, script.scene_dialogue)

        return video

    except Exception as e:
        db.rollback()
        app_logger(e)
        raise HTTPException(
            status_code=500,
            detail=f"Video creation failed: {str(e)}"
        )


async def get(video_id: UUID, db: Session) -> Video:
    """Get video status"""
    return db.query(Video).filter(Video.id == video_id).first()


async def submit_to_heygen(video_id: UUID, scene_dialogue: dict):
    """
    Submit scene dialogue to HeyGen API
    TODO: Implement HeyGen client
    """
    # This will be implemented when we add HeyGen integration
    pass


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
