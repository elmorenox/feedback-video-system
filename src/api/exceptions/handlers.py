# src/api/exceptions/handlers.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from src.schema.base import BaseResponse
from src.logging_config import app_logger


app = FastAPI()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=BaseResponse(
            status=False,
            message=exc.detail,
            data=None,
            error={
                "error_code": str(exc.status_code),
                "error_message": exc.detail,
                "error_details": None
            }
        ).dict()
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the exception
    app_logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=BaseResponse(
            status=False,
            message="Internal server error",
            data=None,
            error={
                "error_code": "500",
                "error_message": str(exc),
                "error_details": None
            }
        ).dict()
    )
