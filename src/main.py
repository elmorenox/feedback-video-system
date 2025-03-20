from fastapi import FastAPI
from fastapi.exceptions import HTTPException

from src.api.routes.video import router as video_router
from src.api.routes.webhooks import router as webhook_router
from src.api.exceptions.handlers import (
    http_exception_handler,
    generic_exception_handler
)


app = FastAPI(title="Feedback Video System")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

app.include_router(video_router)
app.include_router(webhook_router)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
