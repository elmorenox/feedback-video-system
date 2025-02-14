# src/schemas/grading.py
from typing import List, Optional
from pydantic import BaseModel


class StudentInfo(BaseModel):
    name: str
    career_interest: Optional[str]


class Scores(BaseModel):
    current: float
    previous: List[float]


class Component(BaseModel):
    name: str
    score: Optional[float] = None
    grading: Optional[str] = None


class Feedback(BaseModel):
    acc_grading: str
    acc_data: str


class GradingDataSchema(BaseModel):
    student_info: StudentInfo
    scores: Scores
    components: List[Component]
    feedback: Feedback
