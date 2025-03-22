# src/api/routes/video.py
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_sqlite_db
from src.models.video import Video
from src.schema.video import (
    PatchVideoRequest,
    VideoRequestIn,
    VideoData,
    VideoResponse
)
from src.services.dialogue import video as video_handler

router = APIRouter(prefix="/videos")


@router.post("/", response_model=VideoResponse)
async def create_video(
    request: VideoRequestIn,
    db: Session = Depends(get_sqlite_db)
) -> VideoResponse:
    video: Video = await video_handler.create(
        request.student_deployment_id,
        db
    )
    return VideoResponse(
        data=VideoData.model_validate(video)
    )


# New PUT route for complete video replacement
@router.put("/", response_model=VideoResponse)
async def update_video(
    request: VideoRequestIn, db: Session = Depends(get_sqlite_db)
) -> VideoResponse:
    """
    Replace a video completely (regenerates both script and video)
    """
    video = await video_handler.update_video(
        request.student_deployment_id,
        db
    )
    return VideoResponse(
        data=VideoData.model_validate(video),
        message="Video completely updated with new script",
    )


# New PATCH route for partial video updates
@router.patch("/", response_model=VideoResponse)
async def patch_video(
    request: PatchVideoRequest,
    db: Session = Depends(get_sqlite_db),
) -> VideoResponse:
    """
    Partially update a video (by default reuses script, regenerates video)
    """
    # Call patch service
    video: VideoData = await video_handler.patch_video(
        request.student_deployment_id,
        reuse_script=request.reuse_script,
        db=db
    )

    message = "Video updated" + (
        " (reused existing script)"
        if request.reuse_script
        else " (with new script)"
    )
    return VideoResponse(
        data=VideoData.model_validate(video),
        message=message
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video_status(
    video_id: uuid.UUID,
    db: Session = Depends(get_sqlite_db)
):
    video_data = await video_handler.get(video_id, db)
    if not video_data:
        raise HTTPException(status_code=404, detail="Video not found")
    return video_data


@router.delete("/", response_model=VideoResponse)
async def delete_video(
    request: VideoRequestIn, db: Session = Depends(get_sqlite_db)
) -> VideoResponse:
    """
    Permanently delete a video and its associated script.

    Removes the video from HeyGen if it exists and deletes both the video and script from the database.
    """
    await video_handler.delete_video(request.student_deployment_id, db)

    return VideoResponse(
        message=f"Video for deployment {request.student_deployment_id} has been permanently deleted",
        data=None,
    )
