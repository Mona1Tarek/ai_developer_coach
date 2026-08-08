from pydantic import BaseModel
from typing import List


class ReviewRequest(BaseModel):
    code: str


class Mistake(BaseModel):
    title: str
    explanation: str

class ErrorExplanation(BaseModel):
    error_type: str
    explanation: str


class Suggestion(BaseModel):
    title: str
    explanation: str


class ReviewResponse(BaseModel):
    errors_count: int = 0
    error_explanation: List[ErrorExplanation]
    mistakes: List[Mistake]
    strengths: List[str]
    suggestions: List[Suggestion]