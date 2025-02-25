# src/schema/base.py
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

# Generic type for the data field
T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    status: bool = True  # Indicates success (True) or failure (False)
    message: str = "Success"  # Human-readable message
    data: Optional[T] = None  # The actual payload (can be any type)
    error: Optional[dict] = None  # Error details (if any)

    class Config:
        from_attributes = True  # Enable ORM mode if needed
