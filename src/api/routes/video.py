# src/api/routes/video.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_sqlite_db
from src.schema.video import CreateVideoRequest, VideoResponse
from src.services.dialogue import video

router = APIRouter(prefix="/videos")


@router.post("/", response_model=VideoResponse)
async def create_video(
    request: CreateVideoRequest,
    db: Session = Depends(get_sqlite_db)
):
    return await video.create(request.student_deployment_id, db)


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video_status(
    video_id: str,
    db: Session = Depends(get_sqlite_db)
):
    video_data = await video.get(video_id, db)
    if not video_data:
        raise HTTPException(status_code=404, detail="Video not found")
    return video_data
