# src/api/exceptions/handlers.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from src.schema.base import BaseResponse
from src.logging_config import app_logger


app = FastAPI()
