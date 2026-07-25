from pydantic import BaseModel
from typing import List


class ReviewRequest(BaseModel):
    code: str


class Mistake(BaseModel):
    title: str
    explanation: str
    severity: str


class Suggestion(BaseModel):
    title: str
    explanation: str


class ReviewResponse(BaseModel):
    summary: str
    errors_count: int = 0
    mistakes: List[Mistake]
    strengths: List[str]
    suggestions: List[Suggestion]