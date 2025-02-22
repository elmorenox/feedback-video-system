from fastapi import FastAPI
from src.api.routes.video import router as video_router

app = FastAPI(title="Feedback Video System")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

app.include_router(video_router)
