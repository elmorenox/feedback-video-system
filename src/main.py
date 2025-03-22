from fastapi import FastAPI
from fastapi.exceptions import HTTPException

from src.api.routes.video import router as video_router
from src.api.routes.webhooks import router as webhook_router


app = FastAPI(title="Feedback Video System")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

app.include_router(video_router)
app.include_router(webhook_router)
