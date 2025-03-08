# src/api/routes/video.py
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_sqlite_db
from src.models.video import Video
from src.schema.video import CreateVideoRequest, VideoData, VideoResponse
from src.services.dialogue import video as video_handler

router = APIRouter(prefix="/videos")


@router.post("/", response_model=VideoResponse)
async def create_video(
    request: CreateVideoRequest,
    db: Session = Depends(get_sqlite_db)
):
    video: Video = await video_handler.create(
        request.student_deployment_id,
        db
    )
    return VideoResponse(
        data=VideoData.model_validate(video)
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
